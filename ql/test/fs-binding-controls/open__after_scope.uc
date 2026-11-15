import { open } from 'fs';
{ let open = function(x) { return 'shadow'; }; printf('local=%s\n', open("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"));
}
printf('native=%s\n', type(open("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
