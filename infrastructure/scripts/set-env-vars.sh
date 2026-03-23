#!/bin/bash

# PE-GPT デプロイメント用環境変数設定スクリプト
# このスクリプトは環境変数設定の例を示します

echo "PE-GPT デプロイメント用環境変数設定"
echo "======================================"

# 環境の選択
echo "デプロイ対象の環境を選択してください:"
echo "1) development (HTTPS無効)"
echo "2) staging (HTTPS有効)"
echo "3) production (HTTPS有効)"
read -p "選択 (1-3): " ENV_CHOICE

case $ENV_CHOICE in
  1)
    ENVIRONMENT="development"
    echo "Development環境が選択されました。"
    echo "この環境ではHTTPSは無効です。"
    ;;
  2)
    ENVIRONMENT="staging"
    echo "Staging環境が選択されました。"
    ;;
  3)
    ENVIRONMENT="production"
    echo "Production環境が選択されました。"
    ;;
  *)
    echo "無効な選択です。"
    exit 1
    ;;
esac

# 基本的な環境変数
echo ""
echo "基本設定:"
read -p "Bedrock Knowledge Base ID (オプション): " BEDROCK_KB_ID

if [[ "$ENVIRONMENT" == "staging" || "$ENVIRONMENT" == "production" ]]; then
  echo ""
  echo "HTTPS設定 (必須):"
  read -p "ACM Certificate ARN: " CERTIFICATE_ARN
  
  echo ""
  echo "ドメイン設定 (オプション - 空白の場合はデフォルト設定を使用):"
  read -p "カスタムドメイン名: " DOMAIN_NAME
  read -p "コールバックURL (カンマ区切り): " CALLBACK_URLS
  read -p "ログアウトURL (カンマ区切り): " LOGOUT_URLS
fi

# 環境変数の設定コマンドを生成
echo ""
echo "以下のコマンドを実行して環境変数を設定してください:"
echo "=================================================="

if [[ -n "$BEDROCK_KB_ID" ]]; then
  echo "export BEDROCK_KB_ID=\"$BEDROCK_KB_ID\""
fi

if [[ "$ENVIRONMENT" == "staging" || "$ENVIRONMENT" == "production" ]]; then
  if [[ -n "$CERTIFICATE_ARN" ]]; then
    echo "export CERTIFICATE_ARN=\"$CERTIFICATE_ARN\""
  fi
  
  if [[ -n "$DOMAIN_NAME" ]]; then
    echo "export DOMAIN_NAME=\"$DOMAIN_NAME\""
  fi
  
  if [[ -n "$CALLBACK_URLS" ]]; then
    echo "export CALLBACK_URLS=\"$CALLBACK_URLS\""
  fi
  
  if [[ -n "$LOGOUT_URLS" ]]; then
    echo "export LOGOUT_URLS=\"$LOGOUT_URLS\""
  fi
fi

echo ""
echo "設定後、以下のコマンドでデプロイを実行してください:"
echo "./deploy-with-env.sh -e $ENVIRONMENT"

echo ""
echo "または、環境変数を一時的に設定してデプロイする場合:"
ENV_VARS=""
if [[ -n "$BEDROCK_KB_ID" ]]; then
  ENV_VARS="${ENV_VARS}BEDROCK_KB_ID=\"$BEDROCK_KB_ID\" "
fi
if [[ -n "$CERTIFICATE_ARN" ]]; then
  ENV_VARS="${ENV_VARS}CERTIFICATE_ARN=\"$CERTIFICATE_ARN\" "
fi
if [[ -n "$DOMAIN_NAME" ]]; then
  ENV_VARS="${ENV_VARS}DOMAIN_NAME=\"$DOMAIN_NAME\" "
fi
if [[ -n "$CALLBACK_URLS" ]]; then
  ENV_VARS="${ENV_VARS}CALLBACK_URLS=\"$CALLBACK_URLS\" "
fi
if [[ -n "$LOGOUT_URLS" ]]; then
  ENV_VARS="${ENV_VARS}LOGOUT_URLS=\"$LOGOUT_URLS\" "
fi

if [[ -n "$ENV_VARS" ]]; then
  echo "${ENV_VARS}./deploy-with-env.sh -e $ENVIRONMENT"
fi