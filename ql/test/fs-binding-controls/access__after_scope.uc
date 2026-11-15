import { access } from 'fs';
{ let access = function(x) { return 'shadow'; }; printf('local=%s\n', access("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
}
printf('native=%s\n', type(access("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
