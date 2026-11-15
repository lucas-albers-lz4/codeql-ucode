import { readfile } from 'fs';
let f = readfile => readfile("fixtures/native.txt");
printf("local=%s\n", f(function(x) { return 'shadow'; }));
