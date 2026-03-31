import { io } from "socket.io-client";
import fs from "fs";

const config = JSON.parse(fs.readFileSync("config.json", "utf-8"));
// We need the buyer key, not the current Neo key
const BUYER_KEY = fs.readFileSync("/tmp/buyer_key.txt", "utf-8").trim();

console.log("[eval] Connecting as buyer/evaluator with key ..."+BUYER_KEY.slice(-8));

const socket = io("https://claw-api.virtuals.io", {
  auth: { "x-api-key": BUYER_KEY },
  transports: ["websocket"],
});

socket.on("connect", () => {
  console.log("[eval] Connected! Socket ID:", socket.id);
});

socket.on("onEvaluate", async (data: any, callback: any) => {
  console.log(`[eval] onEvaluate for job ${data.id} phase=${data.phase}`);
  if (callback) callback(true);
});

socket.on("onNewTask", async (data: any, callback: any) => {
  console.log(`[eval] onNewTask for job ${data.id} phase=${data.phase}`);
  if (callback) callback(true);
});

socket.on("connect_error", (err: any) => {
  console.error("[eval] Error:", err.message);
  process.exit(1);
});

console.log("[eval] Waiting 60s for events...");
setTimeout(() => { console.log("[eval] Done"); socket.disconnect(); process.exit(0); }, 60000);
