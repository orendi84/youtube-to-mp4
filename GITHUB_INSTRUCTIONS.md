# GitHub Setup Instructions

Follow these steps to create a GitHub repository and push your code:

1. Go to [GitHub.com](https://github.com/) and sign in to your account
2. Click the "+" icon in the top-right corner and select "New repository"
3. Enter "youtube-to-mp4" as the repository name
4. Add a description: "Python tool to download YouTube videos as MP4 files"
5. Choose visibility (Public or Private)
6. Do NOT initialize with README, .gitignore, or license (we already have these files)
7. Click "Create repository"

After creating the repository, GitHub will show you commands to run. Use these commands in your terminal:

```bash
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/youtube-to-mp4.git
git branch -M main
git push -u origin main
```

Once completed, your code will be available on GitHub! 