import { readfile } from 'fs';
try { die('test'); } catch(readfile) { try { readfile("fixtures/native.txt"); } catch(e) { print('catch=not-callable\n'); } }
printf('native=%s\n', type(readfile("fixtures/native.txt")));
