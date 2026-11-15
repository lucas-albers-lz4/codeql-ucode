import { readfile } from 'fs';
{ let readfile = function(x) { return 'shadow'; }; printf('local=%s\n', readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
}
printf('native=%s\n', type(readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
