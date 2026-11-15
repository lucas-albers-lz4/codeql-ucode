import { readlink } from 'fs';
{ let readlink = function(x) { return 'shadow'; }; printf('local=%s\n', readlink("fixtures/native-link"));
}
