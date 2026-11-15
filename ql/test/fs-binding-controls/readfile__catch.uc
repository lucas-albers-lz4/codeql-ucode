import { readfile } from 'fs';
try { die('test'); } catch(readfile) { try { readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt"); } catch(e) { print('catch=not-callable\n'); } }
printf('native=%s\n', type(readfile("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native.txt")));
