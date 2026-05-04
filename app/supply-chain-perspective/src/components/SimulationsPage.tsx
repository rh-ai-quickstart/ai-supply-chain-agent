import type { FormEvent } from 'react';
import { useCallback, useEffect, useState } from 'react';
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
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import { Table, Tbody, Td, Th, Thead, Tr } from '@patternfly/react-table';
import { useTranslation } from 'react-i18next';
import { createSimulation, listSimulations } from '../services/simulationsApi';
import type { SimulationRecord } from '../types/simulations';
import './simulations.css';

export default function SimulationsPage() {
  const { t } = useTranslation('plugin__supply-chain-perspective');
  const [simulations, setSimulations] = useState<SimulationRecord[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [submitError, setSubmitError] = useState('');

  const refresh = useCallback(async () => {
    try {
      setLoadError('');
      const rows = await listSimulations();
      setSimulations(rows);
    } catch {
      setLoadError(t('Unable to load simulations.'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || saving) {
      return;
    }
    setSubmitError('');
    setSaving(true);
    try {
      await createSimulation({ name: trimmed, description: description.trim() });
      setName('');
      setDescription('');
      await refresh();
    } catch {
      setSubmitError(t('Unable to save simulation.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <DocumentTitle>{t('Simulations')}</DocumentTitle>
      <PageSection>
        <div className="supply-chain-perspective__simulations-root supply-chain-perspective__simulations-stack">
          <Card>
            <CardTitle>{t('Create simulation')}</CardTitle>
            <CardBody>
              <p className="supply-chain-perspective__simulations-help">
                {t('Simulations are stored in the API container under /tmp for demo only.')}
              </p>
              {submitError ? (
                <Alert
                  className="supply-chain-perspective__simulations-alert"
                  variant="danger"
                  title={submitError}
                />
              ) : null}
              <Form onSubmit={(e) => void handleSubmit(e)}>
                <FormGroup label={t('Name')} isRequired fieldId="simulation-name">
                  <TextInput
                    id="simulation-name"
                    value={name}
                    onChange={(_event, value) => setName(value)}
                    aria-label={t('Name')}
                  />
                </FormGroup>
                <FormGroup label={t('Description')} fieldId="simulation-description">
                  <TextArea
                    id="simulation-description"
                    value={description}
                    onChange={(_event, value) => setDescription(value)}
                    aria-label={t('Description')}
                    rows={4}
                  />
                </FormGroup>
                <Button type="submit" variant="primary" isDisabled={saving || !name.trim()}>
                  {saving ? t('Saving…') : t('Save simulation')}
                </Button>
              </Form>
            </CardBody>
          </Card>

          <Card>
            <CardTitle>{t('Saved simulations')}</CardTitle>
            <CardBody>
              {loadError ? <Alert variant="danger" title={loadError} /> : null}
              {loading ? (
                <p>{t('Loading simulations…')}</p>
              ) : simulations.length === 0 ? (
                <p>{t('No simulations yet.')}</p>
              ) : (
                <Table aria-label={t('Saved simulations')} borders gridBreakPoint="grid-md">
                  <Thead>
                    <Tr>
                      <Th>{t('Name')}</Th>
                      <Th>{t('Description')}</Th>
                      <Th>{t('Created')}</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {simulations.map((row) => (
                      <Tr key={row.id}>
                        <Td dataLabel={t('Name')}>{row.name}</Td>
                        <Td dataLabel={t('Description')}>
                          {row.description ? row.description : t('No description')}
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
