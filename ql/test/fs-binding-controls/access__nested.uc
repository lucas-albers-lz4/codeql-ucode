import { access } from 'fs';
function outer() { printf('native=%s\n', type(access("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
 }
outer();
