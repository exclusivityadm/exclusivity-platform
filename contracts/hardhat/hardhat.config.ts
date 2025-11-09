import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";
dotenv.config();

const ALCHEMY_HTTP_URL = process.env.ALCHEMY_HTTP_URL || "";
const PRIVATE_KEY = process.env.PRIVATE_KEY || "";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: { optimizer: { enabled: true, runs: 200 } }
  },
  networks: {
    base: {
      url: ALCHEMY_HTTP_URL,
      chainId: 8453,
      accounts: PRIVATE_KEY ? [ "0x" + PRIVATE_KEY ] : []
    }
  }
};

export default config;
