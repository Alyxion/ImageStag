# TODO

## Export: 16-bit PNG

Add 16-bit (48/64-bit color) PNG export support. Implement via Rust (WASM) encoder
to reuse the existing cross-platform filter architecture. The `fast-png` Node.js
library is already used for parity tests but its bare module specifiers (`fflate`,
`iobuffer`) don't resolve in the browser without a bundler.
