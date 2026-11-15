import { readfile } from 'fs';
function readfile(x) { return "shadow"; }
printf('local=%s\n', readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
