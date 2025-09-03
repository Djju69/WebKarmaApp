# Setup script for WebKarmaApp frontend
Write-Host "Setting up WebKarmaApp frontend..." -ForegroundColor Cyan

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install --save-dev typescript @types/react @types/node @types/react-dom @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint eslint-config-next

# Install runtime dependencies
Write-Host "Installing runtime dependencies..." -ForegroundColor Yellow
npm install next react react-dom @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react next-themes

# Create necessary directories
$directories = @(
    "src/app/api",
    "src/components/ui",
    "src/lib",
    "src/styles",
    "public/images"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "Created directory: $dir" -ForegroundColor Green
    }
}

Write-Host "\nSetup completed successfully!" -ForegroundColor Green
Write-Host "Run 'npm run dev' to start the development server." -ForegroundColor Cyan
