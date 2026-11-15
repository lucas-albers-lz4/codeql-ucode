import { readfile } from 'fs';
switch (1) { case 1: let readfile = function(x) { return 'shadow'; }; case 2: printf('local=%s\n', readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
 break; }
printf('native=%s\n', type(readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
