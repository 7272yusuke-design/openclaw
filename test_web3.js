const { ethers } = require("ethers");

// Baseネットワークのプロバイダー（公開RPC）
const provider = new ethers.JsonRpcProvider("https://mainnet.base.org");

async function checkBaseNetwork() {
    try {
        const blockNumber = await provider.getBlockNumber();
        const network = await provider.getNetwork();
        
        console.log("### Node.js Web3 Connectivity Test ###");
        console.log(`Network Name: ${network.name}`);
        console.log(`Chain ID: ${network.chainId}`);
        console.log(`Current Block Number: ${blockNumber}`);
        console.log("\nSuccess: Connected to Base Network via Node.js");
    } catch (error) {
        console.error("Connection failed:", error);
    }
}

checkBaseNetwork();
