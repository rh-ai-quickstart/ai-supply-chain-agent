import type { KeyboardEvent } from 'react';
import { Button, Card, CardBody, CardTitle, Content, Form, TextArea } from '@patternfly/react-core';
import { useTranslation } from 'react-i18next';
import type { ChatMessage } from '../../types/dashboard';

export interface ChatBarProps {
  chatInput: string;
  onChangeChatInput: (_value: string) => void;
  onSubmitChat: () => void;
  chatLoading: boolean;
  chatError: string;
  chatMessages: ChatMessage[];
}

export function ChatBar({
  chatInput,
  onChangeChatInput,
  onSubmitChat,
  chatLoading,
  chatError,
  chatMessages,
}: ChatBarProps) {
  const { t } = useTranslation('plugin__supply-chain-perspective');

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSubmitChat();
    }
  };

  return (
    <Card className="supply-chain-perspective__dashboard-chat-card">
      <CardTitle>{t('Supply chain assistant')}</CardTitle>
      <CardBody>
        <div className="supply-chain-perspective__dashboard-chat-history">
          {chatMessages.length === 0 ? (
            <Content component="p" className="supply-chain-perspective__dashboard-muted">
              {t('No chat messages yet.')}
            </Content>
          ) : (
            chatMessages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`supply-chain-perspective__dashboard-chat-msg supply-chain-perspective__dashboard-chat-msg--${message.role}`}
              >
                <Content component="small">
                  <strong>{message.role === 'human' ? t('You') : t('AI')}</strong>
                </Content>
                <Content component="p">{message.content}</Content>
              </div>
            ))
          )}
        </div>
        {chatError ? (
          <Content
            component="small"
            className="supply-chain-perspective__dashboard-error supply-chain-perspective__dashboard-chat-error"
          >
            {chatError}
          </Content>
        ) : null}
        <Form className="supply-chain-perspective__dashboard-chat-form">
          <TextArea
            aria-label={t('Chat input')}
            placeholder={t('Ask about logistics, demand, routing, or risk...')}
            value={chatInput}
            onChange={(_e, value) => onChangeChatInput(value)}
            onKeyDown={handleKeyDown}
            isDisabled={chatLoading}
            rows={2}
            resizeOrientation="vertical"
          />
          <Button
            variant="primary"
            onClick={onSubmitChat}
            isDisabled={chatLoading || !chatInput.trim()}
          >
            {chatLoading ? t('Sending…') : t('Send')}
          </Button>
        </Form>
      </CardBody>
    </Card>
  );
}
