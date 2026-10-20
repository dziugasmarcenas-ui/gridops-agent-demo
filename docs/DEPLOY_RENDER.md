# Private Render Demo Deployment

This deployment serves the compiled React app and FastAPI API from one web
service. Render Postgres stores the synthetic incidents, ticket drafts, and
procedure embeddings.

## Deploy

1. Push or merge the reviewed deployment branch to GitHub. This repository's
   existing `main` branch does not yet include these deployment files.
2. In Render, create a Blueprint from the repository and select the branch
   containing `render.yaml`.
3. Keep the listed services on the `free` plan for a temporary preview, then
   enter `GRIDOPS_DEMO_AUTH_PASSWORD` and `GRIDOPS_OPENAI_API_KEY` when Render
   requests the unsynchronized environment values. The password is never
   included in the frontend build.
4. Deploy. The container enables pgvector, loads the synthetic procedure
   chunks, inserts any missing synthetic incidents, and then starts FastAPI.
5. In the web service's Custom Domains settings, add
   `gridops.dziugasmarcenas.cm`. Copy the DNS record Render provides into the
   domain's DNS settings, leaving the root domain's existing records alone.
   Render issues HTTPS after the record is verified.
6. Open the custom domain. The browser's Basic Auth prompt protects the page
   and API. Use username `demo` and the password entered in Render.

`/health` remains unauthenticated so Render can check service health. All
other routes require the configured credentials. Local development remains
open unless `GRIDOPS_REQUIRE_DEMO_AUTH=true` is set.

## Cost and lifecycle

The Blueprint uses free Render services to avoid provisioning paid resources
by default. Render's free web service can spin down when idle, and its free
Postgres database expires 30 days after creation. This is suitable for a
temporary preview, not a durable always-on portfolio deployment. See
[Render's free service limits](https://render.com/docs/free) before creating
the Blueprint.
