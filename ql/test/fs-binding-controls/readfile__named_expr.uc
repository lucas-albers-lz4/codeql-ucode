import { readfile } from 'fs';
let f = function readfile(x) { return x ? "shadow" : readfile(1); };
printf("local=%s\n", f(0));
