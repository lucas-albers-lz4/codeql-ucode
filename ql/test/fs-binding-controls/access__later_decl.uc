import { access } from 'fs';
printf('native=%s\n', type(access("fixtures/native.txt")));
let access = function(x) { return 'shadow'; };
printf('local=%s\n', access("fixtures/native.txt"));
