import { readfile } from 'fs';
readfile=function(x) { return 'shadow'; };
printf('local=%s\n', readfile("fixtures/native.txt"));
