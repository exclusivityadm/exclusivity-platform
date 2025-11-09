import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("🚀 Deploying LUXToken contract...");
  console.log("👤 Deployer address:", deployer.address);

  const owner = process.env.OWNER_ADDRESS || deployer.address;
  const name = "LUX";
  const symbol = "LUX";

  const factory = await ethers.getContractFactory("LUXToken");
  const contract = await factory.deploy(name, symbol, owner);
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("✅ LUXToken deployed at:", address);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
