import { readlink } from 'f\x2fs';
printf('wrong=%s\n', readlink("/root/.hermes/profiles/work/cache/scratch/issue85-prep-20261115/native-link"));
