import { cursor } from 'uci';
function run() { let make = cursor; let ctx = make(); ctx.commit('ok'); }
