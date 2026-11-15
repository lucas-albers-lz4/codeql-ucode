import { readlink } from 'fs';
try { for (let readlink in { a: 1 }): print(readlink("probe-link"), "\n"); endfor } catch (e) { print("variable-shadow\n"); }
print(readlink("probe-link"), "\n");
