import { readfile } from 'fs';
let f = readfile => readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt");
printf("local=%s\n", f(function(x) { return 'shadow'; }));
