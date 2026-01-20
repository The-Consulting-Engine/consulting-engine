"""Initiative selection and sizing."""
import json
from typing import Dict, List, Any, Tuple, Optional
from app.core.vertical_config import VerticalConfig, Initiative
from app.llm.client import LLMClient
from app.initiatives.specificity import SpecificityBuilder


class InitiativeSelector:
    """Select and size initiatives from playbook."""
    
    def __init__(
        self,
        vertical_config: VerticalConfig,
        llm_client: LLMClient,
        run_context: Optional[Dict[str, Any]] = None
    ):
        self.config = vertical_config
        self.llm_client = llm_client
        self.run_context = run_context or {}
        self.specificity_builder = SpecificityBuilder(run_context)
    
    def select_and_size(
        self,
        mode_info: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        available_data: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Select initiatives from playbook and size them.
        
        Args:
            mode_info: Operating mode information
            analytics_facts: List of computed facts
            available_data: List of available pack types
        
        Returns:
            List of selected and sized initiatives
        """
        # Step 1: Deterministic eligibility filtering (with blacklist from questions)
        eligible = self._filter_eligible(mode_info, available_data)
        
        # Step 2: Limit based on confidence/mode
        max_initiatives = self._get_max_initiatives(mode_info)
        
        # Step 3: LLM selection with explanations (playbook initiatives)
        selected = self._llm_select(eligible, analytics_facts, max_initiatives)
        
        # Step 4: Sandbox initiatives (if enabled)
        sandbox_enabled = self.run_context.get("derived", {}).get("sandbox_enabled", False)
        if sandbox_enabled and self.llm_client.available:
            sandbox_initiatives = self._generate_sandbox_initiatives(
                analytics_facts,
                mode_info,
                max_sandbox=2
            )
            # Add sandbox initiatives to selected
            selected.extend(sandbox_initiatives)
        
        # Step 5: Deterministic sizing
        sized = self._size_initiatives(selected, analytics_facts)
        
        # Step 6: Build specificity drafts
        with_specifics = self._build_specificity(sized, analytics_facts, mode_info["mode"])
        
        # Step 7: Rank by priority
        ranked = self._rank_initiatives(with_specifics)
        
        return ranked
    
    def _filter_eligible(
        self,
        mode_info: Dict[str, Any],
        available_data: List[str]
    ) -> List[Initiative]:
        """Filter initiatives by eligibility rules and run context blacklist."""
        eligible = []
        months = mode_info.get('months_available', 0)
        
        # Get blacklist from run context
        blacklist = self.run_context.get("derived", {}).get("initiative_blacklist", [])
        
        for initiative in self.config.initiatives:
            # Check blacklist first
            if initiative.id in blacklist:
                continue
            
            rules = initiative.eligibility_rules
            
            # Check minimum months
            min_months = rules.get('min_months', 0)
            if months < min_months:
                continue
            
            # Check required data packs
            requires_data = rules.get('requires_data', [])
            if requires_data and not all(pack in available_data for pack in requires_data):
                continue
            
            # Check required signals (we'll be lenient here)
            requires_signals = rules.get('requires_signals', [])
            # For now, just mark as eligible if basic requirements met
            
            eligible.append(initiative)
        
        return eligible
    
    def _get_max_initiatives(self, mode_info: Dict[str, Any]) -> int:
        """Get maximum initiatives based on mode."""
        mode = mode_info['mode']
        assumptions = self.config.default_assumptions
        
        if mode == "PNL_MODE":
            return assumptions.get('max_initiatives_pnl', 7)
        elif mode == "OPS_MODE":
            return assumptions.get('max_initiatives_ops', 5)
        else:  # DIRECTIONAL_MODE
            return assumptions.get('max_initiatives_directional', 3)
    
    def _llm_select(
        self,
        eligible: List[Initiative],
        analytics_facts: List[Dict[str, Any]],
        max_count: int
    ) -> List[Dict[str, Any]]:
        """Use LLM to select initiatives and write explanations."""
        if not eligible:
            return []
        
        prompt = self._build_selection_prompt(eligible, analytics_facts, max_count)
        
        try:
            response = self.llm_client.generate(
                prompt,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            selections = result.get('selected_initiatives', [])
            
            # Map back to full initiative data
            initiative_map = {init.id: init for init in eligible}
            
            selected = []
            for sel in selections[:max_count]:
                init_id = sel.get('initiative_id')
                if init_id in initiative_map:
                    init = initiative_map[init_id]
                    selected.append({
                        'initiative_id': init.id,
                        'title': init.title,
                        'category': init.category,
                        'description': init.description,
                        'sizing_method': init.sizing_method,
                        'sizing_params': init.sizing_params,
                        'priority_weight': init.priority_weight,
                        'explanation': sel.get('explanation', ''),
                        'assumptions': sel.get('assumptions', []),
                        'data_gaps': sel.get('data_gaps', [])
                    })
            
            return selected
        
        except Exception as e:
            # Fallback: select top initiatives by priority weight
            sorted_eligible = sorted(eligible, key=lambda x: x.priority_weight, reverse=True)
            return [{
                'initiative_id': init.id,
                'title': init.title,
                'category': init.category,
                'description': init.description,
                'sizing_method': init.sizing_method,
                'sizing_params': init.sizing_params,
                'priority_weight': init.priority_weight,
                'explanation': 'Selected based on priority weight (LLM unavailable)',
                'assumptions': ['Limited data analysis'],
                'data_gaps': ['Full diagnostic analysis unavailable']
            } for init in sorted_eligible[:max_count]]
    
    def _build_selection_prompt(
        self,
        eligible: List[Initiative],
        analytics_facts: List[Dict[str, Any]],
        max_count: int
    ) -> str:
        """Build prompt for initiative selection."""
        # Format eligible initiatives
        initiatives_desc = []
        for init in eligible:
            initiatives_desc.append(
                f"- ID: {init.id}\n"
                f"  Title: {init.title}\n"
                f"  Category: {init.category}\n"
                f"  Description: {init.description}"
            )
        
        initiatives_text = "\n\n".join(initiatives_desc)
        
        # Format analytics facts
        facts_desc = []
        for fact in analytics_facts:
            facts_desc.append(
                f"- {fact['evidence_key']}: {fact['label']} = {fact.get('value', fact.get('value_text', 'N/A'))} {fact.get('unit', '')}"
            )
        
        facts_text = "\n".join(facts_desc)
        
        prompt = f"""You are a business diagnostics expert. Select up to {max_count} initiatives from the playbook.

ELIGIBLE INITIATIVES:
{initiatives_text}

ANALYTICS FACTS (evidence keys you MUST reference):
{facts_text}

INSTRUCTIONS:
1. Select the most impactful initiatives based on the analytics facts
2. For each selected initiative, provide:
   - Clear explanation citing specific evidence keys
   - Key assumptions being made
   - Data gaps or limitations
3. Prioritize initiatives with strongest evidence
4. Select up to {max_count} initiatives maximum
5. ONLY select initiatives from the eligible list above

OUTPUT FORMAT (strict JSON):
{{
  "selected_initiatives": [
    {{
      "initiative_id": "rest_labor_scheduling",
      "explanation": "Labor costs are volatile (evidence: labor_volatility) and represent X% of revenue (evidence: labor_pct), suggesting scheduling optimization could yield significant savings.",
      "assumptions": ["Current scheduling is manual", "Peak hours analysis available"],
      "data_gaps": ["Hourly labor distribution not available"]
    }}
  ]
}}

Respond with valid JSON only."""
        
        return prompt
    
    def _size_initiatives(
        self,
        selected: List[Dict[str, Any]],
        analytics_facts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply deterministic sizing to selected initiatives."""
        # Build facts lookup
        facts_map = {fact['evidence_key']: fact for fact in analytics_facts}
        
        for initiative in selected:
            method = initiative['sizing_method']
            params = initiative['sizing_params']
            
            if method == 'percentage_of_revenue':
                # Find average revenue
                revenue_fact = facts_map.get('revenue_avg_monthly')
                if revenue_fact:
                    base = revenue_fact['value'] * 12  # Annualize
                    initiative['impact_low'] = base * params['low']
                    initiative['impact_mid'] = base * params['mid']
                    initiative['impact_high'] = base * params['high']
                    initiative['impact_unit'] = 'annual_savings'
                else:
                    # Fallback
                    initiative['impact_low'] = params['low'] * 100000
                    initiative['impact_mid'] = params['mid'] * 100000
                    initiative['impact_high'] = params['high'] * 100000
                    initiative['impact_unit'] = 'annual_savings'
            
            elif method == 'percentage_of_labor':
                labor_fact = facts_map.get('labor_avg_monthly')
                if labor_fact:
                    base = labor_fact['value'] * 12
                    initiative['impact_low'] = base * params['low']
                    initiative['impact_mid'] = base * params['mid']
                    initiative['impact_high'] = base * params['high']
                    initiative['impact_unit'] = 'annual_savings'
                else:
                    initiative['impact_low'] = params['low'] * 50000
                    initiative['impact_mid'] = params['mid'] * 50000
                    initiative['impact_high'] = params['high'] * 50000
                    initiative['impact_unit'] = 'annual_savings'
            
            elif method == 'percentage_of_cogs':
                # Try to find COGS from facts
                cogs_value = None
                for fact in analytics_facts:
                    if 'cogs' in fact['evidence_key'].lower():
                        cogs_value = fact.get('value')
                        break
                
                if cogs_value:
                    base = cogs_value * 12
                    initiative['impact_low'] = base * params['low']
                    initiative['impact_mid'] = base * params['mid']
                    initiative['impact_high'] = base * params['high']
                    initiative['impact_unit'] = 'annual_savings'
                else:
                    initiative['impact_low'] = params['low'] * 80000
                    initiative['impact_mid'] = params['mid'] * 80000
                    initiative['impact_high'] = params['high'] * 80000
                    initiative['impact_unit'] = 'annual_savings'
            
            elif method == 'fixed_value':
                initiative['impact_low'] = params['low']
                initiative['impact_mid'] = params['mid']
                initiative['impact_high'] = params['high']
                initiative['impact_unit'] = 'annual_savings'
            
            else:
                # Unknown method, use defaults
                initiative['impact_low'] = 5000
                initiative['impact_mid'] = 15000
                initiative['impact_high'] = 30000
                initiative['impact_unit'] = 'annual_savings'
        
        return selected
    
    def _generate_sandbox_initiatives(
        self,
        analytics_facts: List[Dict[str, Any]],
        mode_info: Dict[str, Any],
        max_sandbox: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Generate experimental sandbox initiatives using LLM.
        
        Sandbox initiatives must:
        - Be explicitly labeled "Sandbox / Experimental"
        - Include rationale for why it's worth testing
        - List required data to validate
        - Default to MEDIUM confidence
        """
        # Build sandbox generation prompt
        prompt = self._build_sandbox_prompt(analytics_facts, mode_info, max_sandbox)
        
        try:
            response = self.llm_client.generate(
                prompt,
                temperature=0.4,  # Slightly higher for creativity
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response)
            sandbox_initiatives = result.get("sandbox_initiatives", [])
            
            # Convert to our initiative format
            formatted = []
            for idx, sb_init in enumerate(sandbox_initiatives[:max_sandbox]):
                formatted.append({
                    "initiative_id": f"sandbox_{idx + 1}",
                    "title": f"🧪 {sb_init.get('title', 'Sandbox Initiative')}",
                    "category": "MARKETING",  # Most sandbox are marketing experiments
                    "type": "MARKETING",
                    "description": sb_init.get('description', ''),
                    "lane": "sandbox",
                    "explanation": sb_init.get('rationale', ''),
                    "assumptions": [
                        "This is an experimental initiative",
                        "Requires validation with additional data"
                    ] + sb_init.get('assumptions', []),
                    "data_gaps": sb_init.get('data_needed', []),
                    "priority_weight": 1.0,
                    "sizing_method": "fixed_value",
                    "sizing_params": {
                        "low": 5000,
                        "mid": 15000,
                        "high": 30000
                    }
                })
            
            return formatted
        
        except Exception as e:
            # If LLM fails, return empty list (no sandbox initiatives)
            return []
    
    def _build_sandbox_prompt(
        self,
        analytics_facts: List[Dict[str, Any]],
        mode_info: Dict[str, Any],
        max_count: int
    ) -> str:
        """Build prompt for sandbox initiative generation."""
        facts_text = "\n".join([
            f"- {fact['label']}: {fact.get('value_text', fact.get('value', 'N/A'))} ({fact['evidence_key']})"
            for fact in analytics_facts[:15]
        ])
        
        marketing_channels = self.run_context.get("marketing", {}).get("marketing_channels", [])
        primary_objective = self.run_context.get("goals", {}).get("primary_objective", "unknown")
        
        prompt = f"""You are generating experimental "sandbox" initiatives for a business.

AVAILABLE CONTEXT:
- Primary objective: {primary_objective}
- Marketing channels available: {', '.join(marketing_channels) if marketing_channels else 'unknown'}
- Operating mode: {mode_info['mode']}

ANALYTICS FACTS:
{facts_text}

INSTRUCTIONS:
1. Propose up to {max_count} creative, experimental initiatives
2. Focus on marketing experiments, local outreach, or customer engagement tests
3. Each initiative must be:
   - Specific and actionable
   - Testable with a budget of $500-$2000
   - Measurable with clear success metrics
4. For each initiative provide:
   - Title (creative, specific)
   - Description (what and why)
   - Rationale (why this is worth testing)
   - Data needed (what data would validate this)
   - Assumptions (what we're assuming)

OUTPUT FORMAT (strict JSON):
{{
  "sandbox_initiatives": [
    {{
      "title": "Local Partnership Campaign",
      "description": "Test partnership with nearby businesses to cross-promote",
      "rationale": "Low-cost way to reach adjacent customer base",
      "data_needed": ["Customer demographics", "Partnership ROI tracking"],
      "assumptions": ["Adjacent businesses willing to partner", "Customer overlap exists"]
    }}
  ]
}}

Respond with valid JSON only."""
        
        return prompt
    
    def _build_specificity(
        self,
        sized: List[Dict[str, Any]],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ) -> List[Dict[str, Any]]:
        """Build specific action drafts for each initiative."""
        for initiative in sized:
            draft = self.specificity_builder.build_draft(
                initiative,
                analytics_facts,
                mode
            )
            initiative['specificity_draft'] = draft
        
        return sized
    
    def _rank_initiatives(self, sized: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank initiatives by priority score with context-based boosts."""
        # Get priority boosts from run context
        priority_boost = self.run_context.get("derived", {}).get("initiative_priority_boost", [])
        
        # Calculate priority score based on mid-point impact and weight
        for init in sized:
            impact = init.get('impact_mid', 0)
            weight = init.get('priority_weight', 1.0)
            
            # Apply boost if this initiative is in the boost list
            if init['initiative_id'] in priority_boost:
                weight *= 1.3  # 30% boost
            
            # Sandbox initiatives default to MEDIUM confidence and lower priority
            if init.get('lane') == 'sandbox':
                # Sandbox initiatives don't outrank top playbook unless high confidence
                confidence = init.get('specificity_draft', {}).get('confidence', 'MEDIUM')
                if confidence != 'HIGH':
                    weight *= 0.7  # 30% penalty to keep below top playbook initiatives
            
            init['priority_score'] = impact * weight
        
        # Sort by priority score
        ranked = sorted(sized, key=lambda x: x['priority_score'], reverse=True)
        
        # Assign ranks
        for i, init in enumerate(ranked):
            init['rank'] = i + 1
        
        return ranked
