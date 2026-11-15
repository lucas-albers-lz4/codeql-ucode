import { readlink } from 'fs';
printf('native=%s\n', type(readlink("fixtures/native-link")));
let readlink = function(x) { return 'shadow'; };
printf('local=%s\n', readlink("fixtures/native-link"));
