import { readfile } from 'fs';
try { for (let readfile in { a: 1 }): print(readfile("probe-link"), "\n"); endfor } catch (e) { print("variable-shadow\n"); }
print(readfile("probe-link"), "\n");
