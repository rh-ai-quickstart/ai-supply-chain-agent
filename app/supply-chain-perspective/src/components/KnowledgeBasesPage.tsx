import type { FormEvent } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { DocumentTitle } from '@openshift-console/dynamic-plugin-sdk';
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardTitle,
  Form,
  FormGroup,
  PageSection,
  TextInput,
} from '@patternfly/react-core';
import { Table, Tbody, Td, Th, Thead, Tr } from '@patternfly/react-table';
import { useTranslation } from 'react-i18next';
import { createKnowledgeBase, listKnowledgeBases } from '../services/knowledgeBasesApi';
import type { KnowledgeBaseRecord } from '../types/knowledgeBases';
import './knowledge-bases.css';

export default function KnowledgeBasesPage() {
  const { t } = useTranslation('plugin__supply-chain-perspective');
  const nameFieldId = 'supply-chain-kb-display-name';
  const fileFieldId = 'supply-chain-kb-documents';
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState<KnowledgeBaseRecord[]>([]);
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [submitError, setSubmitError] = useState('');
  const [warnings, setWarnings] = useState<string[]>([]);
  const [hasFiles, setHasFiles] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setLoadError('');
      const list = await listKnowledgeBases();
      setRows(list);
    } catch {
      setLoadError(t('Unable to load knowledge bases.'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- mount fetch updates list/loading/error
    void refresh();
  }, [refresh]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = name.trim();
    const files = fileInputRef.current?.files ?? null;
    if (!trimmed || saving || !files?.length) {
      return;
    }
    setSubmitError('');
    setWarnings([]);
    setSaving(true);
    try {
      const result = await createKnowledgeBase(trimmed, files);
      setName('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      setHasFiles(false);
      if (result.warnings?.length) {
        setWarnings(result.warnings);
      }
      await refresh();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : t('Unable to create knowledge base.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <DocumentTitle>{t('Knowledge bases')}</DocumentTitle>
      <PageSection>
        <div className="supply-chain-perspective__knowledge-bases-root supply-chain-perspective__knowledge-bases-stack">
          <Card>
            <CardTitle>{t('Create knowledge base')}</CardTitle>
            <CardBody>
              <p className="supply-chain-perspective__knowledge-bases-help">
                {t(
                  'Upload text or PDF files. LlamaStack creates a vector store, chunks and embeds content, and stores vectors in the configured provider (e.g. pgvector). The catalog below is stored in the API container for demo only.',
                )}
              </p>
              {submitError ? (
                <Alert
                  className="supply-chain-perspective__knowledge-bases-alert"
                  variant="danger"
                  title={submitError}
                />
              ) : null}
              {warnings.length > 0 ? (
                <Alert
                  className="supply-chain-perspective__knowledge-bases-alert"
                  variant="warning"
                  title={t('Some files were skipped or failed')}
                >
                  <ul>
                    {warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </Alert>
              ) : null}
              <Form onSubmit={(e) => void handleSubmit(e)}>
                <FormGroup label={t('Display name')} isRequired fieldId={nameFieldId}>
                  <TextInput
                    id={nameFieldId}
                    value={name}
                    onChange={(_event, value) => setName(value)}
                    aria-label={t('Display name')}
                  />
                </FormGroup>
                <FormGroup label={t('Documents')} isRequired fieldId={fileFieldId}>
                  <input
                    id={fileFieldId}
                    ref={fileInputRef}
                    className="supply-chain-perspective__knowledge-bases-file-input"
                    type="file"
                    multiple
                    accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf"
                    aria-label={t('Documents')}
                    onChange={() => setHasFiles(!!fileInputRef.current?.files?.length)}
                  />
                </FormGroup>
                <Button
                  type="submit"
                  variant="primary"
                  isDisabled={saving || !name.trim() || !hasFiles}
                >
                  {saving ? t('Uploading…') : t('Create and ingest')}
                </Button>
              </Form>
            </CardBody>
          </Card>

          <Card>
            <CardTitle>{t('Registered knowledge bases')}</CardTitle>
            <CardBody>
              {loadError ? <Alert variant="danger" title={loadError} /> : null}
              {loading ? (
                <p>{t('Loading knowledge bases…')}</p>
              ) : rows.length === 0 ? (
                <p>{t('No knowledge bases yet.')}</p>
              ) : (
                <Table
                  aria-label={t('Registered knowledge bases')}
                  borders
                  gridBreakPoint="grid-md"
                >
                  <Thead>
                    <Tr>
                      <Th>{t('Display name')}</Th>
                      <Th>{t('Vector store ID')}</Th>
                      <Th>{t('Files')}</Th>
                      <Th>{t('Created')}</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {rows.map((row) => (
                      <Tr key={row.id}>
                        <Td dataLabel={t('Display name')}>{row.name}</Td>
                        <Td dataLabel={t('Vector store ID')}>
                          <code className="supply-chain-perspective__knowledge-bases-code">
                            {row.vector_store_id}
                          </code>
                        </Td>
                        <Td dataLabel={t('Files')}>
                          {row.files?.length
                            ? row.files.map((f) => f.filename).join(', ')
                            : t('No files')}
                        </Td>
                        <Td dataLabel={t('Created')}>
                          {new Date(row.createdAt).toLocaleString(undefined, {
                            dateStyle: 'medium',
                            timeStyle: 'short',
                          })}
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              )}
            </CardBody>
          </Card>
        </div>
      </PageSection>
    </>
  );
}
