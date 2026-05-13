import type { KeyboardEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import { Button, Content, Modal, ModalVariant, TextInput, Title } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import type { ChatCompletionPayload, ChatMessage, VectorStoreSummary } from '../../types/dashboard';
import { formatCompletionSummary } from './chatCompletionMeta';
import { ChatMarkdownBody } from './ChatMarkdownBody';

/** Thread row for the chat log (includes optional stack ``completion`` on AI turns). */
type ChatBarMessage = ChatMessage & { completion?: ChatCompletionPayload | null };

export interface ChatBarProps {
  chatInput: string;
  onChangeChatInput: (_value: string) => void;
  onSubmitChat: () => void;
  chatLoading: boolean;
  chatError: string;
  chatMessages: ChatBarMessage[];
  vectorStores: VectorStoreSummary[];
  vectorStoresLoading: boolean;
  vectorStoresError: string;
  selectedVectorStoreId: string;
  onChangeVectorStore: (_id: string) => void;
}

function messageBubbleClassName(role: ChatBarMessage['role'], compact?: boolean): string {
  const base = 'supply-chain-perspective__dashboard-chat-bubble';
  const roleMod = `supply-chain-perspective__dashboard-chat-bubble--${role}`;
  const compactMod = compact ? ' supply-chain-perspective__dashboard-chat-bubble--compact' : '';
  return `${base} ${roleMod}${compactMod}`;
}

export function ChatBar({
  chatInput,
  onChangeChatInput,
  onSubmitChat,
  chatLoading,
  chatError,
  chatMessages,
  vectorStores,
  vectorStoresLoading,
  vectorStoresError,
  selectedVectorStoreId,
  onChangeVectorStore,
}: ChatBarProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const logEndRef = useRef<HTMLDivElement | null>(null);
  const modalInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isChatModalOpen && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [chatMessages, chatLoading, isChatModalOpen]);

  useEffect(() => {
    if (isChatModalOpen) {
      window.setTimeout(() => modalInputRef.current?.focus(), 0);
    }
  }, [isChatModalOpen]);

  const openModal = () => setIsChatModalOpen(true);
  const closeModal = () => setIsChatModalOpen(false);

  const handleSend = () => {
    const trimmed = chatInput.trim();
    if (!trimmed || chatLoading) {
      return;
    }
    if (!isChatModalOpen) {
      openModal();
    }
    onSubmitChat();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const renderVectorStoreRow = () => (
    <div className="supply-chain-perspective__dashboard-chat-vector-row">
      <label
        className="supply-chain-perspective__dashboard-chat-vector-label"
        htmlFor="supply-chain-chat-vector-store"
      >
        {t('Knowledge base')}
      </label>
      <select
        id="supply-chain-chat-vector-store"
        className="supply-chain-perspective__dashboard-chat-vector-select"
        value={selectedVectorStoreId}
        onChange={(event) => onChangeVectorStore(event.target.value)}
        disabled={chatLoading || vectorStoresLoading}
        aria-label={t('Knowledge base')}
        aria-busy={vectorStoresLoading}
        data-test="chat-vector-store"
      >
        <option value="">{t('Default (dashboard PGVector)')}</option>
        {vectorStores.map((store) => (
          <option key={store.id} value={store.id}>
            {store.status && store.status !== 'completed'
              ? `${store.name} (${store.status})`
              : store.name}
          </option>
        ))}
      </select>
      {vectorStoresError ? (
        <span className="supply-chain-perspective__dashboard-chat-vector-error" role="status">
          {vectorStoresError}
        </span>
      ) : null}
    </div>
  );

  const renderMessageLog = (compact: boolean) => (
    <>
      {chatMessages.length === 0 ? (
        <Content component="p" className="supply-chain-perspective__dashboard-muted">
          {t('No chat messages yet.')}
        </Content>
      ) : (
        chatMessages.map((message, index) => {
          const hasCompletion =
            message.role === 'ai' &&
            message.completion &&
            Object.keys(message.completion).length > 0;
          const completionSummary = hasCompletion
            ? formatCompletionSummary(message.completion)
            : '';
          return (
            <div
              key={`${message.role}-${index}`}
              className={messageBubbleClassName(message.role, compact)}
            >
              {message.role === 'ai' ? (
                <>
                  <ChatMarkdownBody content={message.content} compact={compact} />
                  {hasCompletion && message.completion ? (
                    <div className="supply-chain-perspective__dashboard-chat-completion-meta">
                      {completionSummary ? (
                        <Content
                          component="p"
                          className="supply-chain-perspective__dashboard-chat-completion-summary"
                        >
                          {completionSummary}
                        </Content>
                      ) : null}
                      {!compact ? (
                        <details className="supply-chain-perspective__dashboard-chat-completion-details">
                          <summary>{t('Response details')}</summary>
                          <pre>{JSON.stringify(message.completion, null, 2)}</pre>
                        </details>
                      ) : null}
                    </div>
                  ) : null}
                </>
              ) : (
                message.content
              )}
            </div>
          );
        })
      )}
      {chatLoading ? (
        <Content component="p" className="supply-chain-perspective__dashboard-muted">
          {t('Thinking…')}
        </Content>
      ) : null}
      {chatError ? (
        <Content component="p" className="supply-chain-perspective__dashboard-error">
          {chatError}
        </Content>
      ) : null}
      <div ref={compact ? undefined : logEndRef} />
    </>
  );

  return (
    <>
      <div className="supply-chain-perspective__dashboard-chat-bar-container">
        {renderVectorStoreRow()}
        {!isChatModalOpen && chatMessages.length > 0 ? (
          <div
            className="supply-chain-perspective__dashboard-chat-bar-preview"
            data-test="chat-collapsed-preview"
          >
            {renderMessageLog(true)}
          </div>
        ) : null}
        <div className="supply-chain-perspective__dashboard-chat-bar-row">
          <TextInput
            className="supply-chain-perspective__dashboard-chat-bar-input"
            aria-label={t('Chat input')}
            placeholder={t('Ask about logistics, demand, routing, or risk...')}
            type="text"
            value={chatInput}
            onChange={(_e, value) => onChangeChatInput(value)}
            onKeyDown={handleKeyDown}
            isDisabled={chatLoading}
          />
          <Button
            className="supply-chain-perspective__dashboard-chat-send-btn"
            variant="primary"
            onClick={handleSend}
            isDisabled={chatLoading || !chatInput.trim()}
            aria-label={t('Send')}
          >
            {chatLoading ? t('Sending…') : '➤'}
          </Button>
          {chatMessages.length > 0 ? (
            <Button variant="link" onClick={openModal} data-test="chat-open-history">
              {t('View conversation')}
            </Button>
          ) : null}
        </div>
      </div>

      <Modal
        isOpen={isChatModalOpen}
        onClose={closeModal}
        variant={ModalVariant.large}
        ouiaId="supply-chain-chat-modal"
        appendTo={() => document.body}
        aria-labelledby="supply-chain-chat-modal-title"
      >
        <div className="supply-chain-perspective__dashboard-chat-modal-inner">
          <Title headingLevel="h2" size="lg" id="supply-chain-chat-modal-title">
            {t('AI Assistant')}
          </Title>
          <div className="supply-chain-perspective__dashboard-chat-modal-log">
            {renderMessageLog(false)}
          </div>
          <div className="supply-chain-perspective__dashboard-chat-modal-composer">
            <TextInput
              innerRef={modalInputRef}
              className="supply-chain-perspective__dashboard-chat-modal-composer-input"
              aria-label={t('Chat input')}
              placeholder={t('Ask about logistics, demand, routing, or risk...')}
              type="text"
              value={chatInput}
              onChange={(_e, value) => onChangeChatInput(value)}
              onKeyDown={handleKeyDown}
              isDisabled={chatLoading}
            />
            <Button
              variant="primary"
              onClick={handleSend}
              isDisabled={chatLoading || !chatInput.trim()}
              aria-label={t('Send')}
            >
              {chatLoading ? t('Sending…') : t('Send')}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
