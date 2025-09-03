#!/bin/bash

# Setup script for WebKarmaApp frontend
echo -e "\033[36mSetting up WebKarmaApp frontend...\033[0m"

# Install dependencies
echo -e "\033[33mInstalling dependencies...\033[0m"
npm install --save-dev typescript @types/react @types/node @types/react-dom @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint eslint-config-next

# Install runtime dependencies
echo -e "\033[33mInstalling runtime dependencies...\033[0m"
npm install next react react-dom @radix-ui/react-slot class-variance-authority clsx tailwind-merge lucide-react next-themes

# Create necessary directories
directories=(
  "src/app/api"
  "src/components/ui"
  "src/lib"
  "src/styles"
  "public/images"
)

for dir in "${directories[@]}"; do
  if [ ! -d "$dir" ]; then
    mkdir -p "$dir"
    echo -e "\033[32mCreated directory: $dir\033[0m"
  fi
done

echo -e "\n\033[32mSetup completed successfully!\033[0m"
echo -e "\033[36mRun 'npm run dev' to start the development server.\033[0m"
