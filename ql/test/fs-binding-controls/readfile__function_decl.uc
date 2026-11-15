import { readfile } from 'fs';
function readfile(x) { return "shadow"; }
printf('local=%s\n', readfile("fixtures/native.txt"));
