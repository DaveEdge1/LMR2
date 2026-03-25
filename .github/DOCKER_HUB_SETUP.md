# Docker Hub Setup for GitHub Actions

This guide explains how to configure your GitHub repository to automatically push Docker images to Docker Hub.

## Prerequisites

1. A Docker Hub account (create one at https://hub.docker.com if you don't have one)
2. Admin access to your GitHub repository

## Step 1: Create a Docker Hub Access Token

1. Log in to Docker Hub (https://hub.docker.com)
2. Click on your username in the top right corner
3. Select **Account Settings**
4. Navigate to **Security** tab
5. Click **New Access Token**
6. Give it a description (e.g., "GitHub Actions - LMR2")
7. Set the access permissions:
   - **Access permissions**: Read, Write, Delete (or Read & Write minimum)
8. Click **Generate**
9. **IMPORTANT**: Copy the token immediately - you won't be able to see it again!

## Step 2: Add Secrets to GitHub Repository

1. Go to your GitHub repository
2. Click on **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**

### Add DOCKER_USERNAME

1. **Name**: `DOCKER_USERNAME`
2. **Secret**: Your Docker Hub username (e.g., `johndoe`)
3. Click **Add secret**

### Add DOCKER_PASSWORD

1. Click **New repository secret** again
2. **Name**: `DOCKER_PASSWORD`
3. **Secret**: Paste the access token you generated in Step 1
4. Click **Add secret**

## Step 3: Verify Setup

You should now have two secrets in your repository:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`

## Step 4: Create Docker Hub Repository (Optional)

You can either:
- Let GitHub Actions create it automatically on first push, OR
- Create it manually:
  1. Log in to Docker Hub
  2. Click **Create Repository**
  3. **Repository Name**: `lmr2-cfr` (must match IMAGE_NAME in workflow)
  4. **Visibility**: Public or Private (your choice)
  5. Click **Create**

## Step 5: Test the Workflow

1. Make a commit and push to your `main` or `develop` branch:
   ```bash
   git add .
   git commit -m "Add Docker Hub CI/CD"
   git push origin main
   ```

2. Go to your GitHub repository
3. Click on the **Actions** tab
4. You should see a workflow running called "Docker Build and Test"
5. Click on it to see the progress
6. Once complete, check Docker Hub - your image should be there!

## Expected Image Location

After successful build, your image will be available at:
```
docker.io/<your-username>/lmr2-cfr:latest
```

You can pull it with:
```bash
docker pull <your-username>/lmr2-cfr:latest
```

## Image Tags

The workflow automatically creates these tags:
- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `develop` - Latest build from develop branch
- `sha-<commit>` - Specific commit SHA
- `pr-<number>` - Pull request builds (not pushed to Docker Hub)

## Troubleshooting

### Error: "unauthorized: authentication required"

**Problem**: Docker Hub credentials are incorrect or missing.

**Solution**:
1. Verify `DOCKER_USERNAME` and `DOCKER_PASSWORD` secrets are set correctly
2. Make sure the access token hasn't expired
3. Check that the token has write permissions

### Error: "denied: requested access to the resource is denied"

**Problem**: The username doesn't have permission to push to the repository.

**Solution**:
1. Verify the Docker Hub username is correct
2. Check that the repository name matches
3. Create the repository manually on Docker Hub first

### Build succeeds but image not on Docker Hub

**Problem**: The workflow only pushes on main/develop branches, not on pull requests.

**Solution**: This is expected behavior. The workflow tests PRs but only pushes from protected branches.

## Security Best Practices

1. **Use Access Tokens**: Never use your Docker Hub password directly
2. **Limit Token Scope**: Create tokens with minimum required permissions
3. **Rotate Tokens**: Regenerate tokens periodically
4. **Use Secrets**: Never commit credentials to your repository
5. **Review Access**: Regularly audit who has access to your GitHub repository

## Advanced Configuration

### Change Image Name

Edit `.github/workflows/docker-build.yml`:
```yaml
env:
  IMAGE_NAME: your-new-image-name
```

### Push to Multiple Registries

You can modify the workflow to push to both Docker Hub and GitHub Container Registry:
```yaml
- name: Extract metadata for Docker
  id: meta
  uses: docker/metadata-action@v5
  with:
    images: |
      ${{ secrets.DOCKER_USERNAME }}/${{ env.IMAGE_NAME }}
      ghcr.io/${{ github.repository_owner }}/${{ env.IMAGE_NAME }}
```

### Add Build Arguments

```yaml
- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    build-args: |
      PYTHON_VERSION=3.11
      BUILD_DATE=${{ github.event.head_commit.timestamp }}
```

## Pulling the Image

Once pushed, anyone can pull your image (if public):

```bash
# Pull latest
docker pull <your-username>/lmr2-cfr:latest

# Pull specific version
docker pull <your-username>/lmr2-cfr:sha-abc1234

# Run it
docker run -it <your-username>/lmr2-cfr:latest
```

## Cost Considerations

- **Docker Hub Free Tier**:
  - Unlimited public repositories
  - 1 private repository
  - 200 container pulls per 6 hours

- **Docker Hub Pro** (if needed):
  - Unlimited private repositories
  - Unlimited pulls
  - ~$5/month

## Monitoring Builds

1. GitHub Actions provides build logs and status
2. Docker Hub shows pull statistics and scan results
3. Set up notifications in GitHub for build failures

## References

- [Docker Hub Tokens Documentation](https://docs.docker.com/docker-hub/access-tokens/)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Docker Build Push Action](https://github.com/docker/build-push-action)

## Need Help?

If you encounter issues:
1. Check the Actions logs in GitHub
2. Review Docker Hub access logs
3. Verify all secrets are set correctly
4. Check the workflow file syntax

## Summary Checklist

- [ ] Docker Hub account created
- [ ] Access token generated
- [ ] `DOCKER_USERNAME` secret added to GitHub
- [ ] `DOCKER_PASSWORD` secret added to GitHub
- [ ] Workflow file committed to repository
- [ ] Test push successful
- [ ] Image visible on Docker Hub
- [ ] Can pull image successfully

Once all boxes are checked, your CI/CD pipeline is ready!
