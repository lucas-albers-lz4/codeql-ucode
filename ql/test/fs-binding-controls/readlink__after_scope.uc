import { readlink } from 'fs';
{ let readlink = function(x) { return 'shadow'; }; printf('local=%s\n', readlink("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native-link"));
}
printf('native=%s\n', type(readlink("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native-link")));
