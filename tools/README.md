# bazzite-deck-nvidia-lts fork

Bazzite Gaming Mode (deck) with the legacy NVIDIA 580 driver (`nvidia-lts`) and
LTS kernel, for Maxwell/Pascal/Volta GPUs (GTX 900/1000) that the official
`bazzite-deck-nvidia` image (nvidia-open only) cannot drive.

Image: `ghcr.io/supercalig/bazzite-deck-nvidia-lts:stable`

```
rpm-ostree rebase ostree-unverified-registry:ghcr.io/supercalig/bazzite-deck-nvidia-lts:stable
```

## How it stays up to date

`.github/workflows/build.yml` runs every Monday (and on manual dispatch):

1. Reads Fedora/kernel versions from upstream's `build.yml` matrix
   (LTS kernel from upstream's `bazzite-nvidia` entry).
2. Checks out upstream `ublue-os/bazzite` `main`.
3. Runs `tools/apply_fork_patches.py` on its Containerfile.
4. Builds and pushes the image.

Only the build workflow is fork-specific. Everything else in this repo outside
`.github/` and `tools/` is not used by the build.

If upstream changes its `build.yml`, the run shows a warning. Compare it with
this fork's `build.yml`, port any needed changes, then update
`tools/upstream-build.sha256`:

```
curl -fsSL https://raw.githubusercontent.com/ublue-os/bazzite/main/.github/workflows/build.yml | sha256sum | cut -d' ' -f1 > tools/upstream-build.sha256
```

## Other tools

- `couch-debug.sh`: collects Gaming Mode / NVIDIA logs (`curl -sL is.gd/Vxwl2H | bash`).
