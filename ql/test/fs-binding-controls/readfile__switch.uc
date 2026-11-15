import { readfile } from 'fs';
switch (1) { case 1: let readfile = function(x) { return 'shadow'; }; case 2: printf('local=%s\n', readfile("fixtures/native.txt"));
 break; }
printf('native=%s\n', type(readfile("fixtures/native.txt")));
