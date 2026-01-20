"""Specificity builder for generating concrete action drafts."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class SpecificityBuilder:
    """Generate specific, actionable drafts for initiatives."""
    
    def __init__(self, run_context: Optional[Dict[str, Any]] = None):
        """
        Initialize builder with run context.
        
        Args:
            run_context: Derived context from intake questions
        """
        self.context = run_context or {}
        self.derived = self.context.get("derived", {})
        self.constraints = self.context.get("constraints", {})
        self.operations = self.context.get("operations", {})
        self.marketing = self.context.get("marketing", {})
        self.goals = self.context.get("goals", {})
    
    def build_draft(
        self,
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ) -> Dict[str, Any]:
        """
        Build specific action draft for an initiative.
        
        Returns:
            {
                what: str - specific action description,
                where: str - scope/location/channel/category,
                how_much: str - quantified range or target,
                timing: str - when to implement,
                next_steps: List[str] - concrete checklist,
                assumptions: List[str] - key assumptions,
                data_needed: List[str] - additional data required,
                confidence: str - LOW/MEDIUM/HIGH,
                specificity_level: str - DIRECTIONAL/SPECIFIC/DETAILED
            }
        """
        initiative_id = initiative.get("id", "")
        initiative_type = initiative.get("type", "")
        
        # Build base draft structure
        draft = {
            "what": "",
            "where": "",
            "how_much": "",
            "timing": "",
            "next_steps": [],
            "assumptions": [],
            "data_needed": [],
            "confidence": "MEDIUM",
            "specificity_level": "DIRECTIONAL"
        }
        
        # Deterministically populate based on initiative type
        if initiative_type == "LABOR_OPTIMIZATION":
            self._populate_labor_draft(draft, initiative, analytics_facts, mode)
        elif initiative_type == "PRICING":
            self._populate_pricing_draft(draft, initiative, analytics_facts, mode)
        elif initiative_type == "THROUGHPUT":
            self._populate_throughput_draft(draft, initiative, analytics_facts, mode)
        elif initiative_type == "COST_REDUCTION":
            self._populate_cost_reduction_draft(draft, initiative, analytics_facts, mode)
        elif initiative_type == "DISCOUNT_CONTROL":
            self._populate_discount_draft(draft, initiative, analytics_facts, mode)
        elif initiative_type == "WASTE_REDUCTION":
            self._populate_waste_draft(draft, initiative, analytics_facts, mode)
        elif initiative_type == "MARKETING":
            self._populate_marketing_draft(draft, initiative, analytics_facts, mode)
        else:
            # Generic template
            self._populate_generic_draft(draft, initiative, analytics_facts, mode)
        
        # Calculate specificity level
        draft["specificity_level"] = self._calculate_specificity(draft)
        
        return draft
    
    def _populate_labor_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate labor optimization specifics."""
        # Extract labor facts
        labor_pct = self._find_fact(analytics_facts, "labor_percent")
        
        # Get quantitative inputs from operations context
        daily_hours = self.operations.get("daily_labor_hours")
        total_employees = self.operations.get("total_employees")
        avg_hourly_rate = self.operations.get("avg_hourly_rate")
        peak_hours = self.operations.get("peak_hours")
        
        draft["what"] = "Optimize labor scheduling and staffing levels"
        
        # Where - based on scheduling method and peak hours
        scheduling = self.operations.get("scheduling_method")
        if scheduling == "manual_fixed":
            where_text = "Focus on peak/off-peak hour staffing (currently using fixed schedules)"
            if peak_hours:
                where_text += f" - Peak identified as {peak_hours}"
            draft["where"] = where_text
        elif scheduling == "manual_demand":
            where_text = "Refine demand-based scheduling patterns (currently manual adjustments)"
            if peak_hours:
                where_text += f" - Focus on {peak_hours}"
            draft["where"] = where_text
        else:
            draft["where"] = "All shifts and positions"
        
        # How much - use specific numbers if available
        if labor_pct and daily_hours and avg_hourly_rate:
            try:
                daily_hours_num = float(daily_hours)
                hourly_rate_num = float(avg_hourly_rate)
                target_reduction = initiative.get("expected_impact", 0.02)
                current = labor_pct.get("value", 0)
                target = current * (1 - target_reduction)
                
                # Calculate potential daily savings
                hours_to_save = daily_hours_num * target_reduction
                daily_savings = hours_to_save * hourly_rate_num
                monthly_savings = daily_savings * 30
                
                draft["how_much"] = (
                    f"Reduce labor % from {current:.1%} to ~{target:.1%}. "
                    f"This means reducing ~{hours_to_save:.1f} hours/day "
                    f"(~${daily_savings:.0f}/day or ${monthly_savings:.0f}/month)"
                )
                draft["confidence"] = "HIGH"
            except (ValueError, TypeError):
                # Fallback if conversion fails
                target_reduction = initiative.get("expected_impact", 0.02)
                current = labor_pct.get("value", 0)
                target = current * (1 - target_reduction)
                draft["how_much"] = f"Reduce labor % from {current:.1%} to ~{target:.1%} ({target_reduction:.1%} reduction)"
                draft["confidence"] = "MEDIUM"
        elif labor_pct:
            target_reduction = initiative.get("expected_impact", 0.02)
            current = labor_pct.get("value", 0)
            target = current * (1 - target_reduction)
            draft["how_much"] = f"Reduce labor % from {current:.1%} to ~{target:.1%} ({target_reduction:.1%} reduction)"
            draft["confidence"] = "MEDIUM"
        else:
            draft["how_much"] = "Target 2-3% labor cost reduction"
            draft["confidence"] = "LOW"
        
        # Timing
        implementation_speed = self.derived.get("assumption_overrides", {}).get("implementation_speed", "moderate")
        if implementation_speed == "fast":
            draft["timing"] = "Implement over next 2-4 weeks (high autonomy)"
        elif implementation_speed == "slow":
            draft["timing"] = "Implement over 6-8 weeks (requires approvals)"
        else:
            draft["timing"] = "Implement over 4-6 weeks"
        
        # Next steps
        draft["next_steps"] = [
            "Analyze hourly revenue/traffic data for last 3 months",
            "Identify peak vs. off-peak patterns by day of week",
            "Create revised schedule template with 15-30 min adjustments",
            "Test schedule for 2 weeks and measure labor %",
            "Adjust based on results"
        ]
        
        # Assumptions
        draft["assumptions"] = [
            "Revenue patterns remain relatively consistent",
            "Ability to adjust schedules without contractual issues",
            "Manager buy-in and training on new approach"
        ]
        
        # Data needed
        draft["data_needed"] = [
            "Hourly revenue/transaction data",
            "Current employee schedules by day",
            "Peak hour staffing levels"
        ]
    
    def _populate_pricing_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate pricing initiative specifics."""
        draft["what"] = "Test selective price increases on high-margin items"
        
        # Check pricing control
        pricing_control = self.constraints.get("pricing_control")
        if pricing_control == "no_control":
            draft["where"] = "NOT APPLICABLE - No pricing control"
            draft["confidence"] = "N/A"
            return
        elif pricing_control == "limited_control":
            draft["where"] = "Items requiring minimal approval (sides, beverages, add-ons)"
        else:
            draft["where"] = "Top 20-30% of menu items by volume"
        
        # How much
        price_increase = initiative.get("expected_impact", 0.03)
        draft["how_much"] = f"Test {price_increase:.1%} price increase on selected items"
        
        # Timing
        draft["timing"] = "Implement as A/B test over 4 weeks"
        
        # Next steps
        draft["next_steps"] = [
            "Identify top-selling items with good margins",
            "Model revenue impact at different price points",
            "Test increase on 5-10 items first",
            "Monitor volume and revenue changes weekly",
            "Roll out to additional items if successful"
        ]
        
        draft["assumptions"] = [
            "Price elasticity is moderate (low customer pushback)",
            "Competitors haven't recently changed prices",
            "Menu mix stays relatively stable"
        ]
        
        draft["data_needed"] = [
            "Item-level sales data",
            "Item margins/costs",
            "Competitor pricing data"
        ]
        
        draft["confidence"] = "MEDIUM" if mode == "PNL_MODE" else "LOW"
    
    def _populate_throughput_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate throughput initiative specifics."""
        # Get quantitative inputs
        seating_capacity = self.operations.get("seating_capacity")
        avg_check_size = self.goals.get("avg_check_size")
        peak_hours = self.operations.get("peak_hours")
        
        draft["what"] = "Increase table turns or order throughput during peak periods"
        
        # Where - based on capacity bottlenecks
        bottlenecks = self.operations.get("capacity_bottlenecks", [])
        if "seating" in bottlenecks:
            where_text = "Focus on seating/table turnover (identified as constraint)"
            if seating_capacity:
                where_text += f" - Current capacity: {seating_capacity} seats"
            if peak_hours:
                where_text += f" during {peak_hours}"
            draft["where"] = where_text
        elif "kitchen" in bottlenecks:
            draft["where"] = "Focus on kitchen prep/cooking speed (identified as constraint)"
        else:
            where_text = "Peak hours (lunch and dinner service)"
            if peak_hours:
                where_text = f"Peak hours: {peak_hours}"
            draft["where"] = where_text
        
        # How much - calculate potential revenue impact if we have data
        throughput_increase = initiative.get("expected_impact", 0.05)
        if seating_capacity and avg_check_size:
            try:
                capacity_num = float(seating_capacity)
                check_num = float(avg_check_size)
                additional_turns = capacity_num * throughput_increase
                daily_revenue = additional_turns * check_num * 2  # Assume 2 peak periods
                monthly_revenue = daily_revenue * 30
                
                draft["how_much"] = (
                    f"Target {throughput_increase:.1%} increase in peak-hour capacity. "
                    f"With {capacity_num:.0f} seats at ${check_num:.2f} avg check, "
                    f"this could add ~${monthly_revenue:.0f}/month in revenue"
                )
                draft["confidence"] = "MEDIUM"
            except (ValueError, TypeError):
                draft["how_much"] = f"Target {throughput_increase:.1%} increase in peak-hour capacity"
                draft["confidence"] = "LOW"
        else:
            draft["how_much"] = f"Target {throughput_increase:.1%} increase in peak-hour capacity"
            draft["confidence"] = "LOW"
        
        # Timing
        draft["timing"] = "Test changes over 3-4 weeks, scale if successful"
        
        # Next steps
        if "seating" in bottlenecks:
            draft["next_steps"] = [
                "Track current table turn times by meal period",
                "Identify bottlenecks (seating, ordering, payment)",
                "Implement quick wins (digital menus, faster payment)",
                "Test for 2 weeks and measure improvement",
                "Adjust service flow based on results"
            ]
        else:
            draft["next_steps"] = [
                "Analyze current peak-hour capacity utilization",
                "Identify operational bottlenecks",
                "Test process improvements",
                "Measure capacity change",
                "Scale successful changes"
            ]
        
        draft["assumptions"] = [
            "Demand exists to fill additional capacity",
            "Quality/experience doesn't suffer from faster throughput",
            "Staff can adapt to new processes"
        ]
        
        draft["data_needed"] = [
            "Peak hour sales data",
            "Table turn times or order completion times",
            "Wait times or lost sales data"
        ]
        
        draft["confidence"] = "MEDIUM"
    
    def _populate_cost_reduction_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate cost reduction specifics."""
        draft["what"] = "Reduce non-essential overhead and operating expenses"
        draft["where"] = "Marketing, supplies, utilities, subscriptions"
        
        # How much
        cost_reduction = initiative.get("expected_impact", 0.05)
        draft["how_much"] = f"Target {cost_reduction:.1%} reduction in overhead costs"
        
        # Timing
        draft["timing"] = "Audit and implement over 4-6 weeks"
        
        # Next steps
        draft["next_steps"] = [
            "Audit all recurring expenses",
            "Identify low-ROI spending",
            "Renegotiate vendor contracts",
            "Eliminate unused subscriptions",
            "Track savings monthly"
        ]
        
        draft["assumptions"] = [
            "Some expenses can be reduced without impacting operations",
            "Vendor contracts are negotiable",
            "Tracking systems in place"
        ]
        
        draft["data_needed"] = [
            "Detailed expense breakdown by category",
            "Vendor contracts and terms",
            "Historical spending trends"
        ]
        
        draft["confidence"] = "MEDIUM" if mode == "PNL_MODE" else "LOW"
    
    def _populate_discount_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate discount control specifics."""
        discount_behavior = self.marketing.get("discount_behavior")
        
        if discount_behavior == "rare":
            draft["what"] = "NOT APPLICABLE - Already minimal discount usage"
            draft["confidence"] = "N/A"
            return
        
        draft["what"] = "Reduce discount frequency and depth"
        
        if discount_behavior == "frequent":
            draft["where"] = "Currently running weekly+ promotions - reduce to bi-weekly or monthly"
        else:
            draft["where"] = "Review all promotional offers"
        
        # How much
        discount_reduction = initiative.get("expected_impact", 0.02)
        draft["how_much"] = f"Target {discount_reduction:.1%} margin improvement from reduced discounting"
        
        # Timing
        draft["timing"] = "Phase out over 6-8 weeks to avoid customer shock"
        
        # Next steps
        draft["next_steps"] = [
            "Analyze current discount impact on margin",
            "Identify which promotions drive incremental volume",
            "Eliminate lowest-ROI discounts first",
            "Test reduced frequency for 4 weeks",
            "Monitor revenue and margin impact"
        ]
        
        draft["assumptions"] = [
            "Some discounts are margin-negative",
            "Customer base isn't overly discount-dependent",
            "Gradual reduction minimizes revenue risk"
        ]
        
        draft["data_needed"] = [
            "Discount usage by type",
            "Margin impact by promotion",
            "Customer behavior with/without discounts"
        ]
        
        draft["confidence"] = "MEDIUM"
    
    def _populate_waste_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate waste reduction specifics."""
        menu_control = self.constraints.get("menu_control")
        
        if menu_control == "no_control":
            draft["what"] = "NOT APPLICABLE - No menu control"
            draft["confidence"] = "N/A"
            return
        
        draft["what"] = "Reduce food waste through better inventory management"
        draft["where"] = "High-spoilage ingredients and low-selling menu items"
        
        # How much
        waste_reduction = initiative.get("expected_impact", 0.02)
        draft["how_much"] = f"Target {waste_reduction:.1%} COGS reduction from waste elimination"
        
        # Timing
        draft["timing"] = "Implement tracking and adjustments over 4 weeks"
        
        # Next steps
        draft["next_steps"] = [
            "Track waste by ingredient/item for 2 weeks",
            "Identify high-waste items",
            "Adjust ordering quantities and frequencies",
            "Consider menu simplification if needed",
            "Monitor waste and COGS monthly"
        ]
        
        draft["assumptions"] = [
            "Current waste is measurable and trackable",
            "Ordering can be adjusted without stockouts",
            "Menu flexibility exists"
        ]
        
        draft["data_needed"] = [
            "Ingredient usage and waste logs",
            "Item-level sales data",
            "Ordering history"
        ]
        
        draft["confidence"] = "MEDIUM" if menu_control == "full_control" else "LOW"
    
    def _populate_marketing_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate marketing initiative specifics."""
        # Get marketing plan schema if present
        plan_schema = initiative.get("plan_schema", {})
        
        if plan_schema:
            # Use plan schema fields - these are pre-populated from playbook
            draft["what"] = initiative.get("description", "Run targeted marketing experiment")
            draft["where"] = f"{plan_schema.get('channel', 'TBD')} targeting {plan_schema.get('target_audience', 'TBD')}"
            draft["how_much"] = f"Budget: {plan_schema.get('budget_range', 'TBD')}"
            draft["timing"] = plan_schema.get("timing_window", "TBD")
            draft["next_steps"] = plan_schema.get("setup_steps", [])
            
            # Add plan-specific assumptions
            success_metric = plan_schema.get("success_metric", "")
            if success_metric:
                draft["assumptions"] = [
                    f"Success metric: {success_metric}",
                    "Marketing channels are accessible",
                    "Ability to track campaign results"
                ]
            else:
                draft["assumptions"] = [
                    "Marketing channels are accessible",
                    "Ability to track campaign results",
                    "Incremental revenue covers costs"
                ]
        else:
            # Generic marketing template for sandbox initiatives
            channels = self.marketing.get("marketing_channels", [])
            monthly_marketing_spend = self.marketing.get("monthly_marketing_spend")
            
            draft["what"] = initiative.get("description", "Run local marketing experiment")
            draft["where"] = f"Active channels: {', '.join(channels) if channels else 'TBD'}"
            
            # Use marketing spend context for budget if available
            if monthly_marketing_spend:
                try:
                    spend_num = float(monthly_marketing_spend)
                    test_budget_low = min(500, spend_num * 0.1)
                    test_budget_high = min(2000, spend_num * 0.3)
                    draft["how_much"] = f"Budget: ${test_budget_low:.0f}-${test_budget_high:.0f} test (10-30% of current monthly spend)"
                except (ValueError, TypeError):
                    draft["how_much"] = "Budget: $500-2000 test"
            else:
                draft["how_much"] = "Budget: $500-2000 test"
            
            draft["timing"] = "4-week test period"
            draft["next_steps"] = [
                "Define specific offer/campaign",
                "Set up tracking",
                "Run test campaign",
                "Measure ROI",
                "Scale if positive"
            ]
            
            # Add current spend context to assumptions if available
            if monthly_marketing_spend:
                draft["assumptions"] = [
                    f"Current monthly marketing spend: ${monthly_marketing_spend}",
                    "Marketing channels are accessible",
                    "Ability to track campaign results",
                    "Incremental revenue covers costs"
                ]
            else:
                draft["assumptions"] = [
                    "Marketing channels are accessible",
                    "Ability to track campaign results",
                    "Incremental revenue covers costs"
                ]
        
        draft["data_needed"] = [
            "Current marketing spend and ROI" if not self.marketing.get("monthly_marketing_spend") else None,
            "Customer acquisition costs",
            "Channel performance data"
        ]
        # Remove None entries
        draft["data_needed"] = [d for d in draft["data_needed"] if d is not None]
        
        draft["confidence"] = "MEDIUM"
    
    def _populate_generic_draft(
        self,
        draft: Dict[str, Any],
        initiative: Dict[str, Any],
        analytics_facts: List[Dict[str, Any]],
        mode: str
    ):
        """Populate generic initiative draft."""
        draft["what"] = initiative.get("name", "Unknown initiative")
        draft["where"] = "To be determined based on specific business context"
        draft["how_much"] = f"Target {initiative.get('expected_impact', 0.03):.1%} improvement"
        draft["timing"] = "4-6 weeks implementation"
        draft["next_steps"] = [
            "Assess current baseline",
            "Identify specific opportunities",
            "Test changes",
            "Measure impact",
            "Scale if successful"
        ]
        draft["assumptions"] = ["Sufficient data and resources available"]
        draft["data_needed"] = ["Detailed operational metrics"]
        draft["confidence"] = "LOW"
    
    def _find_fact(self, analytics_facts: List[Dict[str, Any]], label_contains: str) -> Optional[Dict[str, Any]]:
        """Find analytics fact by label."""
        for fact in analytics_facts:
            if label_contains.lower() in fact.get("label", "").lower():
                return fact
        return None
    
    def _calculate_specificity(self, draft: Dict[str, Any]) -> str:
        """
        Calculate specificity level based on populated fields.
        
        Returns:
            DIRECTIONAL - minimal specifics
            SPECIFIC - good detail
            DETAILED - comprehensive
        """
        # Count populated concrete fields
        concrete_fields = 0
        
        if draft["what"] and "TBD" not in draft["what"] and "NOT APPLICABLE" not in draft["what"]:
            concrete_fields += 1
        
        if draft["where"] and "TBD" not in draft["where"] and "To be determined" not in draft["where"]:
            concrete_fields += 1
        
        if draft["how_much"] and "TBD" not in draft["how_much"]:
            concrete_fields += 1
        
        if draft["timing"] and "TBD" not in draft["timing"]:
            concrete_fields += 1
        
        if len(draft["next_steps"]) >= 3:
            concrete_fields += 1
        
        # Determine level
        if concrete_fields >= 4:
            return "DETAILED"
        elif concrete_fields >= 2:
            return "SPECIFIC"
        else:
            return "DIRECTIONAL"
