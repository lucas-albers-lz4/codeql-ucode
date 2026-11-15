import { open } from 'fs';
function outer() { printf('native=%s\n', type(open("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
 }
outer();
