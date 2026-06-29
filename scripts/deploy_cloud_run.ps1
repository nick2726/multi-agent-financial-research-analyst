param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectId,

    [Parameter(Mandatory = $false)]
    [string]$Region = "asia-south1",

    [Parameter(Mandatory = $false)]
    [string]$ServiceName = "financial-research-analyst",

    [Parameter(Mandatory = $false)]
    [string]$ImageName = "financial-research-analyst"
)

$ErrorActionPreference = "Stop"

Write-Host "Setting gcloud project..."
gcloud config set project $ProjectId

$ImageUri = "gcr.io/$ProjectId/$ImageName"

Write-Host "Building container image: $ImageUri"
gcloud builds submit --tag $ImageUri

Write-Host "Deploying to Cloud Run: $ServiceName"
gcloud run deploy $ServiceName `
  --image $ImageUri `
  --region $Region `
  --platform managed `
  --allow-unauthenticated `
  --port 8080

Write-Host "Deployment complete."
