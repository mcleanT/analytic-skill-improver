## Visualization Standards

All figures MUST follow these standards:

- **Resolution**: 300 DPI minimum; use `save_fig()` which enforces this automatically
- **Fonts**: Arial/Helvetica, 12pt axis labels (bold), 10pt tick labels, 14pt titles (bold)
- **Colors**: Colorblind-safe palettes only — use `get_palette(n)` from the toolkit. Never use red-green combinations or jet/rainbow colormaps
- **Layout**: Use `constrained_layout=True` when creating figures manually
- **Format**: Save as both PDF (vector, for publication) and PNG (300 DPI, for preview) via `save_fig(fig, path)`
