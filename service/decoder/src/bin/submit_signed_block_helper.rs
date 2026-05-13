use std::{fs, path::PathBuf};

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeParameters,
        Metadata,
    },
    proxy::ProxyOperation,
    store_type::StoreType,
};
use anyhow::{anyhow, Context, Result};
use linera_base::{
    crypto::{AccountSecretKey, AccountSignature, CryptoHash},
    data_types::{Amount, Round},
    hex,
    identifiers::{Account, AccountOwner, ApplicationId, ChainId},
};
use linera_chain::data_types::BlockProposal;
use linera_chain::data_types::ProposalContent;
use linera_core::data_types::UnsignedBlockProposal;
use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
struct HelperInput {
    keystore_path: Option<PathBuf>,
    unsigned_block_proposal: Option<UnsignedBlockProposal>,
    block_proposal_json: Option<Value>,
    proposal_content_json: Option<Value>,
    meme_name: String,
    meme_ticker: String,
    logo_hash: CryptoHash,
    blob_gateway_application_id: ApplicationId,
    ams_application_id: ApplicationId,
    swap_application_id: ApplicationId,
    creator_chain_id: ChainId,
    creator_owner: AccountOwner,
    swap_creator_chain_id: ChainId,
}

#[derive(Deserialize)]
struct RawKeystore {
    keys: Vec<(AccountOwner, Vec<u8>)>,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct HelperOutput {
    operation_bytes: Vec<u8>,
    signature: Option<AccountSignature>,
    block_proposal_bcs_hex: Option<String>,
    signed_block_bcs_hex: Option<String>,
}

#[derive(Serialize)]
struct SignedBlockBcsValue {
    unsigned_block_proposal: UnsignedBlockProposal,
    signature: AccountSignature,
    blob_bytes: Vec<Vec<u8>>,
}

fn load_secret_key(path: &PathBuf, owner: AccountOwner) -> Result<AccountSecretKey> {
    let raw = fs::read_to_string(path)
        .with_context(|| format!("failed to read keystore {}", path.display()))?;
    let keystore: RawKeystore = serde_json::from_str(&raw).context("failed to parse keystore")?;

    let bytes = keystore
        .keys
        .into_iter()
        .find_map(|(entry_owner, value)| (entry_owner == owner).then_some(value))
        .ok_or_else(|| anyhow!("owner {owner} not found in keystore"))?;

    let json = String::from_utf8(bytes).context("keystore key payload is not utf8 json")?;
    let secret_key: AccountSecretKey =
        serde_json::from_str(&json).context("failed to decode account secret key")?;
    Ok(secret_key)
}

fn build_operation(input: &HelperInput) -> Result<Vec<u8>> {
    let operation = ProxyOperation::CreateMeme {
        meme_instantiation_argument: MemeInstantiationArgument {
            meme: Meme {
                initial_supply: Amount::from_tokens(21_000_000),
                total_supply: Amount::from_tokens(21_000_000),
                name: input.meme_name.clone(),
                ticker: input.meme_ticker.clone(),
                decimals: 6,
                metadata: Metadata {
                    logo_store_type: StoreType::Blob,
                    logo: Some(input.logo_hash),
                    description: "local submitSignedBlock helper".to_string(),
                    twitter: None,
                    telegram: None,
                    discord: None,
                    website: None,
                    github: None,
                    live_stream: None,
                },
                virtual_initial_liquidity: true,
                initial_liquidity: None,
            },
            blob_gateway_application_id: Some(input.blob_gateway_application_id),
            ams_application_id: Some(input.ams_application_id),
            proxy_application_id: None,
            swap_application_id: Some(input.swap_application_id),
        },
        meme_parameters: MemeParameters {
            creator: Account {
                chain_id: input.creator_chain_id,
                owner: input.creator_owner,
            },
            initial_liquidity: Some(Liquidity {
                fungible_amount: Amount::from_tokens(10_499_900),
                native_amount: Amount::from_tokens(8_720),
            }),
            virtual_initial_liquidity: true,
            swap_creator_chain_id: input.swap_creator_chain_id,
            enable_mining: false,
            mining_supply: Some(Amount::from_tokens(10_499_100)),
        },
    };
    bcs::to_bytes(&operation).context("failed to encode proxy create meme operation")
}

fn sign_unsigned_block(
    unsigned_block_proposal: &UnsignedBlockProposal,
    secret_key: &AccountSecretKey,
) -> Result<AccountSignature> {
    let content: ProposalContent = unsigned_block_proposal.content.clone().into();
    let hash = CryptoHash::new(&content);
    Ok(secret_key.sign_prehash(hash))
}

fn sign_proposal_content(
    content: ProposalContent,
    secret_key: &AccountSecretKey,
) -> Result<AccountSignature> {
    let hash = CryptoHash::new(&content);
    Ok(secret_key.sign_prehash(hash))
}

fn validate_round(unsigned_block_proposal: &UnsignedBlockProposal) -> Result<()> {
    match unsigned_block_proposal.content.round {
        Round::Fast | Round::MultiLeader(_) | Round::SingleLeader(_) | Round::Validator(_) => {
            Ok(())
        }
    }
}

fn main() -> Result<()> {
    let raw = std::env::args()
        .nth(1)
        .ok_or_else(|| anyhow!("expected one json argument"))?;
    let mut input: HelperInput =
        serde_json::from_str(&raw).context("failed to parse helper input")?;

    if input.unsigned_block_proposal.is_none() {
        if let Some(value) = input.block_proposal_json.take() {
            input.unsigned_block_proposal =
                Some(serde_json::from_value(value).context("failed to decode blockProposal json")?);
        }
    }

    let operation_bytes = build_operation(&input)?;
    let signature = match (&input.keystore_path, &input.unsigned_block_proposal, &input.proposal_content_json) {
        (Some(keystore_path), Some(unsigned_block_proposal), None) => {
            validate_round(unsigned_block_proposal)?;
            let secret_key = load_secret_key(keystore_path, input.creator_owner)?;
            Some(sign_unsigned_block(unsigned_block_proposal, &secret_key)?)
        }
        (Some(keystore_path), None, Some(value)) => {
            let content: ProposalContent = serde_json::from_value(value.clone())
                .context("failed to decode proposalContent json")?;
            let secret_key = load_secret_key(keystore_path, input.creator_owner)?;
            Some(sign_proposal_content(content, &secret_key)?)
        }
        (None, None, None) => None,
        _ => {
            return Err(anyhow!(
                "provide either keystorePath + unsignedBlockProposal, or keystorePath + proposalContentJson, or neither"
            ))
        }
    };

    let block_proposal_bcs_hex = match (
        &input.unsigned_block_proposal,
        &input.proposal_content_json,
        &signature,
    ) {
        (Some(unsigned_block_proposal), None, Some(signature)) => {
            let block_proposal = BlockProposal {
                content: unsigned_block_proposal.content.clone().into(),
                signature: signature.clone(),
                original_proposal: unsigned_block_proposal.original_proposal.clone(),
            };
            Some(hex::encode(
                bcs::to_bytes(&block_proposal).context("failed to bcs-encode block proposal")?,
            ))
        }
        (None, Some(value), Some(signature)) => {
            let content: ProposalContent = serde_json::from_value(value.clone())
                .context("failed to decode proposalContent json")?;
            let block_proposal = BlockProposal {
                content,
                signature: signature.clone(),
                original_proposal: None,
            };
            Some(hex::encode(
                bcs::to_bytes(&block_proposal).context("failed to bcs-encode block proposal")?,
            ))
        }
        _ => None,
    };

    let signed_block_bcs_hex = match (&input.unsigned_block_proposal, &signature) {
        (Some(unsigned_block_proposal), Some(signature)) => {
            let signed_block = SignedBlockBcsValue {
                unsigned_block_proposal: unsigned_block_proposal.clone(),
                signature: signature.clone(),
                blob_bytes: Vec::new(),
            };
            Some(hex::encode(
                bcs::to_bytes(&signed_block).context("failed to bcs-encode signed block")?,
            ))
        }
        _ => None,
    };

    let output = HelperOutput {
        operation_bytes,
        signature,
        block_proposal_bcs_hex,
        signed_block_bcs_hex,
    };
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}
