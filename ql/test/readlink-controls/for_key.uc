import { readlink } from 'fs';
try { for (let readlink, value in { a: 1 }) { print(readlink("probe-link"), "\n"); } } catch (e) { print("key-shadow\n"); }
print(readlink("probe-link"), "\n");
