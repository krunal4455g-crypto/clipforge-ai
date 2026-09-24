# ClipForge AI Mobile Deployment

This is the deploy-ready web app version.

## Easiest deployment: Render

1. Create a GitHub repository.
2. Upload all files in this folder.
3. On Render, create a new Web Service from the GitHub repo.
4. Render detects the Dockerfile.
5. Deploy.
6. Open the generated HTTPS URL on your Android phone.

The app is mobile-first. Paste a YouTube URL, choose number of clips, and download generated MP4s.

## Important
- Use only videos you own or have permission to process.
- This MVP uses local Whisper + heuristic scoring.
- Processing can be slow and memory-heavy on low-cost hosting.
- For a production version, move jobs to a queue/worker and object storage, and add an LLM scoring layer.
