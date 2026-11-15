import { readlink } from 'fs';
printf('native=%s\n', type(readlink("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native-link")));
let readlink = function(x) { return 'shadow'; };
printf('local=%s\n', readlink("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native-link"));
