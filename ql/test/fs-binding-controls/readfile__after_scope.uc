import { readfile } from 'fs';
{ let readfile = function(x) { return 'shadow'; }; printf('local=%s\n', readfile("fixtures/native.txt"));
}
printf('native=%s\n', type(readfile("fixtures/native.txt")));
