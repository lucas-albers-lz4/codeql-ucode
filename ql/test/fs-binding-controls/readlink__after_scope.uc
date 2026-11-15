import { readlink } from 'fs';
{ let readlink = function(x) { return 'shadow'; }; printf('local=%s\n', readlink("fixtures/native-link"));
}
printf('native=%s\n', type(readlink("fixtures/native-link")));
