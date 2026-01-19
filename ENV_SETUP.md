# Environment Setup Guide

This guide explains how to set up your environment variables for the Consulting Engine.

## Required Environment Variables

### OpenAI API Key

The system uses OpenAI's API for LLM-assisted features. You need an API key from OpenAI.

#### Getting an OpenAI API Key

1. Go to https://platform.openai.com/
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key (you won't be able to see it again)

#### Setting the API Key

Create a `.env` file in the root directory of the project:

```bash
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Replace `sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx` with your actual API key.

## Optional Environment Variables

### Database Configuration

By default, the system uses PostgreSQL in Docker. You can override:

```bash
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### OpenAI Model Selection

Default is `gpt-4-turbo-preview`. You can change:

```bash
OPENAI_MODEL=gpt-4-turbo-preview
# or
OPENAI_MODEL=gpt-3.5-turbo
```

Note: GPT-4 provides better mapping suggestions and explanations but is more expensive.

### Debug Mode

Enable detailed logging:

```bash
DEBUG=true
```

### File Paths

Override default upload and report directories:

```bash
UPLOAD_DIR=/custom/path/uploads
REPORTS_DIR=/custom/path/reports
```

## Complete .env Example

```bash
# Required
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional - Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/consulting_engine

# Optional - OpenAI
OPENAI_MODEL=gpt-4-turbo-preview

# Optional - Application
DEBUG=true
UPLOAD_DIR=/app/uploads
REPORTS_DIR=/app/reports
```

## Security Best Practices

### Do NOT commit .env files

The `.gitignore` file excludes `.env` files automatically. Never commit sensitive credentials.

### Use Different Keys for Different Environments

- **Development**: Use a development API key with rate limits
- **Production**: Use a production key with monitoring
- **Testing**: Consider using a mock LLM client to avoid API costs

### Rotate API Keys Regularly

OpenAI allows you to create multiple keys and revoke old ones. Rotate keys every 90 days.

## Troubleshooting

### "OpenAI API key not found" Error

**Symptom**: Backend fails to start or LLM features fail.

**Solutions**:
1. Verify `.env` file exists in root directory
2. Check variable name is exactly `OPENAI_API_KEY`
3. Ensure no spaces around `=` in `.env` file
4. Restart Docker containers: `docker-compose restart backend`

### "Invalid API Key" Error

**Symptom**: LLM features fail with authentication error.

**Solutions**:
1. Verify key starts with `sk-`
2. Check key hasn't been revoked in OpenAI dashboard
3. Ensure you have API credits available
4. Try creating a new key

### "Rate Limit Exceeded" Error

**Symptom**: Intermittent LLM failures.

**Solutions**:
1. Check your OpenAI usage limits
2. Add rate limiting to backend (future enhancement)
3. Upgrade OpenAI plan if needed
4. Use GPT-3.5-turbo for lower costs

### Database Connection Issues

**Symptom**: Backend can't connect to database.

**Solutions**:
1. Verify `DATABASE_URL` format is correct
2. Check PostgreSQL is running: `docker-compose ps`
3. Wait 10-15 seconds for database initialization
4. Check database logs: `docker-compose logs db`

## Environment Variable Loading

The system uses `pydantic-settings` to load environment variables:

1. First checks environment variables
2. Then loads from `.env` file
3. Falls back to defaults in `backend/app/core/config.py`

## Docker Compose Integration

The `docker-compose.yml` automatically:
- Loads `.env` file from root directory
- Passes `OPENAI_API_KEY` to backend service
- Sets default values for other variables

You don't need to modify `docker-compose.yml` - just create `.env` file.

## Testing Configuration

To test your configuration:

```bash
# Start services
docker-compose up backend

# Check logs for successful startup
docker-compose logs backend | grep "Application startup complete"

# Test health endpoint
curl http://localhost:8000/api/health

# Test LLM connectivity (requires valid API key)
# Upload a file through the UI and try mapping suggestions
```

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
