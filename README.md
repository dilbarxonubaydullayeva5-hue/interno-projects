# interno-projects

Video project built with [Remotion](https://github.com/remotion-dev/remotion).

## Commands

```bash
npm install       # install dependencies
npm run dev       # open Remotion Studio (preview in browser)
npm run render    # render the HelloWorld composition to out/video.mp4
npm run lint      # type-check
```

Compositions are registered in `src/Root.tsx`.

## Video system

- `VIDEO-SYSTEM.md` — channel rules (rubrics, voice, palette, delivery, metrics).
- `PIPELINE.md` — the nine steps of a video and the four STOP points.
- `script-method.md` — the 13-step script method.
- `log.md` — per-video metrics and system changes.
- `videos/_template/` — copy to `videos/NN-slug/` for each new video.
- `npm run script-lint -- videos/NN-slug/script.md` — script check (must report 0 errors).
- `src/theme.ts` — paper palette, safe zone, 9:16 size.
