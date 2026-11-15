import { popen } from 'fs';
try { for (let popen in { a: 1 }): print(popen("probe-link"), "\n"); endfor } catch (e) { print("variable-shadow\n"); }
print(popen("probe-link"), "\n");
