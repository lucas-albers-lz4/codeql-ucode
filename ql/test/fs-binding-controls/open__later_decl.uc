import { open } from 'fs';
printf('native=%s\n', type(open("fixtures/native.txt")));
let open = function(x) { return 'shadow'; };
printf('local=%s\n', open("fixtures/native.txt"));
