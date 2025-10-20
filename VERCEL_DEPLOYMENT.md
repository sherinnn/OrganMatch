# Vercel Deployment Guide

## Prerequisites
1. Install Vercel CLI: `npm i -g vercel`
2. Create a Vercel account at https://vercel.com

## Deployment Steps

### 1. Login to Vercel
```bash
vercel login
```

### 2. Deploy the app
```bash
vercel
```

### 3. Set Environment Variables
After deployment, you need to set these environment variables in your Vercel dashboard:

- `AGENT_ROLE_ARN=arn:aws:iam::694152115054:role/AgentCoreOrganMatchRole`
- `AWS_REGION=us-east-1`
- `REGION=us-east-1`
- `GATEWAY_ID=organmatch-gateway-lorsb6rxxr`
- `MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0`
- `AGENT_ID=KFMQATUSIF`
- `AGENT_ALIAS_ID=TSTALIASID`
- `ORGANS_TABLE=donors`
- `RECIPIENTS_TABLE=recipients`
- `WEATHER_API_KEY=b0fd96ff58d3457bad2223816251610`

### 4. Alternative: Set via CLI
```bash
vercel env add AGENT_ROLE_ARN
vercel env add AWS_REGION
vercel env add REGION
vercel env add GATEWAY_ID
vercel env add MODEL_ID
vercel env add AGENT_ID
vercel env add AGENT_ALIAS_ID
vercel env add ORGANS_TABLE
vercel env add RECIPIENTS_TABLE
vercel env add WEATHER_API_KEY
```

### 5. Redeploy after setting environment variables
```bash
vercel --prod
```

## Project Structure
- `app.py` - Main Flask application
- `vercel.json` - Vercel configuration
- `requirements.txt` - Python dependencies
- `routes/` - API and page routes
- `templates/` - HTML templates
- `backend/` - Core business logic

## Troubleshooting

If you encounter deployment errors:

1. **Try deploying again** - Sometimes it's a transient error
2. **Check function size** - The app is configured with 50MB max size
3. **Verify environment variables** - Make sure all required env vars are set

## Recent Fixes Applied

- ✅ Lazy AWS initialization to prevent serverless cold start issues
- ✅ Simplified dependencies for better Vercel compatibility  
- ✅ Added function timeout and size limits
- ✅ Graceful handling of missing dependencies

## Notes
- The app is configured to run on Vercel's Python runtime
- All routes are handled through Flask blueprints
- Static files should be placed in the `static/` directory
- Environment variables are loaded from Vercel's environment
- AWS services are initialized lazily to improve cold start performance