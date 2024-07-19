# Thumbnailer

This is a command-line tool to process video files in bulk. It currently produces several files which are 1920p, 29.97 fps, with low quality compression. 

1. A [proxy](https://helpx.adobe.com/after-effects/using/footage-items.html#placeholders_and_proxies) for smoother video editing
2. Some previews for quick browsing. These include a [look-up table (LUT)](https://en.wikipedia.org/wiki/3D_lookup_table) and automatic smoothed brightness [normalization](https://ffmpeg.org/ffmpeg-filters.html#normalize):
   1. Original video
   2. Original video with [Topaz Video AI stabilization](https://docs.topazlabs.com/video-ai/filters/stabilization) (at 100% strength auto-crop with rolling shutter correction)

For me, these files are each ~100× smaller than the original (which on my [Sony A6700](https://www.sony.com/electronics/support/e-mount-body-ilce-6000-series/ilce-6700/specifications) is XAVC-I 4K @ 59.94 fps, which is 600 Mbit/s or ~4.5 GB per minute).
