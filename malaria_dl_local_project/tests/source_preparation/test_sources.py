from __future__ import annotations

import importlib.util
import io
import json
import sys
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO / 'malaria_dl_local_project'), str(REPO / 'malaria_dataset_split_project/src')]
from malaria_split.source_config import CELL_SOURCE, SMEAR_SOURCE, SMEAR_ROOT, resolve_source_config
from src.malaria_dl.data import full_smears_download as full
from src.malaria_dl.data.cell_source import prepare_cell_source


def test_defaults_without_env(tmp_path: Path) -> None:
    config = resolve_source_config(capstone_root=tmp_path, environ={})
    assert config.cell_source == CELL_SOURCE
    assert config.smear_source == SMEAR_SOURCE
    assert config.smear_root == tmp_path / SMEAR_ROOT
    assert not (tmp_path / 'malaria_dataset_split_project/.env').exists()


def test_source_and_root_precedence(tmp_path: Path) -> None:
    env = tmp_path / 'malaria_dataset_split_project/.env'
    env.parent.mkdir()
    env.write_text('THIN_BLOOD_SMEARS_PF_SOURCE=https://example.org/index.html\nTHIN_BLOOD_SMEARS_PF_ROOT="file root"\n')
    config = resolve_source_config(capstone_root=tmp_path, environ={})
    assert config.smear_source == 'https://example.org/index.html'
    assert config.smear_root == tmp_path / 'file root'
    process = {'THIN_BLOOD_SMEARS_PF_ROOT': 'process', 'THIN_BLOOD_SMEARS_PF_SOURCE': 'https://other.org/index.html'}
    assert resolve_source_config(capstone_root=tmp_path, environ=process).smear_root == tmp_path / 'process'
    config = resolve_source_config('cli', capstone_root=tmp_path, environ=process)
    assert config.smear_root == tmp_path / 'cli'
    assert config.smear_source == process['THIN_BLOOD_SMEARS_PF_SOURCE']
    assert resolve_source_config(tmp_path / 'absolute', capstone_root=tmp_path, environ=process).smear_root == tmp_path / 'absolute'


@pytest.fixture
def distribution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple:
    monkeypatch.setattr(full, 'EXPECTED', {'Polygon Set': (1, 5), 'Point Set': (1, 5)})
    config = resolve_source_config(capstone_root=tmp_path, environ={})
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as z:
        for subset in full.EXPECTED:
            for number in range(5):
                z.writestr(f'{subset}/228C86P47ThinF/Img/IMG_{number}.jpg', b'raw-image-bytes')
                z.writestr(f'{subset}/228C86P47ThinF/GT/IMG_{number}.txt', '1,10,10\n1,Uninfected,No_comment,Point,1,2,2\n')
        for name in full.DOCUMENTS:
            z.writestr(name, b'archive document')
    urls = {name: full.urllib.parse.urljoin(config.smear_source, full.urllib.parse.quote(name))
            for name in (*full.DOCUMENTS, full.DATASET + '.zip')}
    index = ''.join(f'<a href="{u}">{n}</a>' for n, u in urls.items()).encode()
    payloads = {config.smear_source: index, urls[full.DATASET + '.zip']: archive.getvalue()}
    payloads.update({urls[name]: b'standalone document' for name in full.DOCUMENTS})
    calls = []

    def fetch(url: str, path: Path) -> dict:
        calls.append(url)
        path.write_bytes(payloads[url])
        return {'url': url, 'effective_url': url, 'retrieved_at': full.utc_now(),
                'size': path.stat().st_size, 'sha256': full.sha256(path),
                'downloaded_files': 1, 'downloaded_bytes': path.stat().st_size}
    return config, fetch, calls


def test_complete_manifest_preserves_source_and_document_versions(distribution: tuple) -> None:
    config, fetch, calls = distribution
    result = full.prepare_full_smear_source(config, fetch=fetch)
    assert result['status'] == 'READY'
    assert len(calls) == 5
    manifest = json.loads((config.smear_root / full.MANIFEST).read_text())
    assert manifest['source'] == config.smear_source
    assert manifest['hash_strategy'] == 'LOCAL_BASELINE_SHA256'
    assert not manifest['official_checksum_available']
    assert len(manifest['files']) == 26
    assert all(v['archive_differs_from_standalone'] for v in manifest['document_versions'])
    assert (config.smear_root / 'ReadMe.pdf').read_bytes() == b'archive document'
    assert (config.smear_root / '.capstone_source_documents/ReadMe.pdf').read_bytes() == b'standalone document'
    assert all(f['size'] > 0 and len(f['sha256']) == 64 for f in manifest['files'])


def test_second_run_no_download(distribution: tuple) -> None:
    config, fetch, _ = distribution
    full.prepare_full_smear_source(config, fetch=fetch)
    forbidden = Mock(side_effect=AssertionError('network forbidden'))
    result = full.prepare_full_smear_source(config, fetch=forbidden)
    assert result['status'] == 'ALREADY_DOWNLOADED'
    assert result['downloaded_files'] == result['downloaded_bytes'] == 0
    forbidden.assert_not_called()


def test_verify_only_no_network_or_modification(distribution: tuple) -> None:
    config, fetch, _ = distribution
    full.prepare_full_smear_source(config, fetch=fetch)
    before = {str(p): (p.stat().st_mtime_ns, full.sha256(p)) for p in config.smear_root.rglob('*') if p.is_file()}
    forbidden = Mock(side_effect=AssertionError('network forbidden'))
    full.prepare_full_smear_source(config, verify_only=True, fetch=forbidden)
    after = {str(p): (p.stat().st_mtime_ns, full.sha256(p)) for p in config.smear_root.rglob('*') if p.is_file()}
    assert before == after
    forbidden.assert_not_called()


def test_verify_only_absent_does_not_create_root(tmp_path: Path) -> None:
    config = resolve_source_config(capstone_root=tmp_path, environ={})
    with pytest.raises(full.SourceError, match='INTEGRITY_FAIL'):
        full.prepare_full_smear_source(config, verify_only=True, fetch=Mock(side_effect=AssertionError))
    assert not config.smear_root.parent.exists()


@pytest.mark.parametrize('mutation', ['changed', 'missing', 'partial', 'untracked'])
def test_corruption_never_ready(distribution: tuple, mutation: str) -> None:
    config, fetch, _ = distribution
    full.prepare_full_smear_source(config, fetch=fetch)
    target = next(config.smear_root.rglob('*.jpg'))
    if mutation == 'changed': target.write_bytes(b'changed')
    elif mutation == 'missing': target.unlink()
    elif mutation == 'partial': target.with_suffix('.jpg.part').write_bytes(b'partial')
    else: (config.smear_root / 'unexpected').write_bytes(b'extra')
    with pytest.raises(full.SourceError, match='INTEGRITY_FAIL'):
        full.prepare_full_smear_source(config, fetch=Mock(side_effect=AssertionError))


def test_structure_mismatch_never_published(distribution: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    config, fetch, _ = distribution
    monkeypatch.setattr(full, 'EXPECTED', {'Polygon Set': (33, 165), 'Point Set': (160, 800)})
    with pytest.raises(full.SourceError, match='DATASET_STRUCTURE_MISMATCH'):
        full.prepare_full_smear_source(config, fetch=fetch)
    assert not config.smear_root.exists()


def test_existing_untracked_source_not_overwritten(tmp_path: Path) -> None:
    config = resolve_source_config(capstone_root=tmp_path, environ={})
    config.smear_root.mkdir(parents=True)
    old = config.smear_root / 'ReadMe.pdf'; old.write_bytes(b'S1 protected evidence')
    with pytest.raises(full.SourceError, match='INTEGRITY_FAIL'):
        full.prepare_full_smear_source(config, fetch=Mock(side_effect=AssertionError))
    assert old.read_bytes() == b'S1 protected evidence'


def test_source_change_conflicts(distribution: tuple) -> None:
    config, fetch, _ = distribution
    full.prepare_full_smear_source(config, fetch=fetch)
    with pytest.raises(full.SourceError, match='SOURCE_VERSION_CONFLICT'):
        full.prepare_full_smear_source(replace(config, smear_source='https://other.org/index.html'), fetch=Mock(side_effect=AssertionError))


def test_cell_arbitrary_source_rejected_before_tfds_import(tmp_path: Path) -> None:
    config = replace(resolve_source_config(capstone_root=tmp_path, environ={}), cell_source='https://other.org/cells.zip')
    with pytest.raises(full.SourceError, match='SOURCE_MISMATCH'):
        prepare_cell_source(config)


@pytest.mark.parametrize('name', ['../escape.jpg', '/absolute.jpg', 'a/../../escape.jpg', 'C:\\escape.jpg', full.MANIFEST, '.capstone_source_documents/ReadMe.pdf'])
def test_unsafe_zip_rejected(tmp_path: Path, name: str) -> None:
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as z: z.writestr(name, b'bad')
    with pytest.raises(full.SourceError, match='INTEGRITY_FAIL'):
        full.extract_archive(archive, tmp_path / 'out')


def test_truncated_http_never_becomes_final_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Response(io.BytesIO):
        status = 200
        headers = {'Content-Length': '100'}
        def geturl(self) -> str: return 'https://example.org/file'
    monkeypatch.setattr(full.urllib.request, 'urlopen', lambda *a, **kw: Response(b'short'))
    monkeypatch.setattr(full.time, 'sleep', lambda seconds: None)
    target = tmp_path / 'download.zip'
    with pytest.raises(full.SourceError, match='DOWNLOAD_FAILED'):
        full.download_file('https://example.org/file', target)
    assert not target.exists()
    assert target.with_name(target.name + '.part').exists()


def orchestrator() -> object:
    spec = importlib.util.spec_from_file_location('s1d_prepare', REPO / 'malaria_dl_local_project/scripts/prepare_datasets.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_orchestrator_delegates_verify_only(monkeypatch: pytest.MonkeyPatch) -> None:
    module = orchestrator()
    cell = Mock(return_value={'status': 'ALREADY_DOWNLOADED'})
    smear = Mock(return_value={'status': 'ALREADY_DOWNLOADED'})
    monkeypatch.setattr(module, 'prepare_cell_source', cell)
    monkeypatch.setattr(module, 'prepare_full_smear_source', smear)
    assert module.main(['--verify-only']) == 0
    assert cell.call_args.kwargs == smear.call_args.kwargs == {'verify_only': True}
    assert cell.call_args.args[0] == smear.call_args.args[0]


def test_reserved_split_has_no_side_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    module = orchestrator()
    forbidden = Mock(side_effect=AssertionError('must not prepare or split'))
    monkeypatch.setattr(module, 'prepare_cell_source', forbidden)
    monkeypatch.setattr(module, 'prepare_full_smear_source', forbidden)
    assert module.main(['--split', '80', '10', '10']) == 2
    forbidden.assert_not_called()


def test_actual_nlm_index_encodes_spaces_once(tmp_path: Path) -> None:
    index = tmp_path / 'index.html'
    index.write_text(''.join(f'<a href="{name}">file</a>' for name in (*full.DOCUMENTS, full.DATASET + '.zip')))
    urls = full.discover_urls(index, SMEAR_SOURCE)
    assert urls['Data License Agreement.docx'].endswith('Data%20License%20Agreement.docx')
    index.write_text(''.join(f'<a href="{full.urllib.parse.quote(name)}">file</a>' for name in (*full.DOCUMENTS, full.DATASET + '.zip')))
    assert full.discover_urls(index, SMEAR_SOURCE) == urls


def test_completed_transfer_reused_after_interruption(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Response(io.BytesIO):
        status = 200
        headers = {'Content-Length': '8'}
        def geturl(self) -> str: return 'https://example.org/file'
    network = Mock(side_effect=lambda *a, **kw: Response(b'complete'))
    monkeypatch.setattr(full.urllib.request, 'urlopen', network)
    target = tmp_path / 'file.zip'
    target.with_name('file.zip.part').write_bytes(b'incomplete old transfer')
    assert full.download_file('https://example.org/file', target)['downloaded_files'] == 1
    assert full.download_file('https://example.org/file', target)['downloaded_files'] == 0
    assert network.call_count == 1
    assert target.read_bytes() == b'complete'


def test_cached_cell_source_verifies_all_records_without_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from src.malaria_dl.data import cell_source
    cache = tmp_path / 'tfds'; (cache / 'malaria/1.0.0').mkdir(parents=True)
    monkeypatch.setattr(cell_source, 'get_tfds_data_dir', lambda: cache)
    image = SimpleNamespace(ndim=3, shape=(3, 4, 3))
    info = SimpleNamespace(version='1.0.0', features={'label': SimpleNamespace(names=['parasitized', 'uninfected'])},
                           splits={'train': SimpleNamespace(num_examples=27558)})
    builder = SimpleNamespace(info=info, as_dataset=Mock(return_value='records'))
    tfds = SimpleNamespace(builder_from_directory=Mock(return_value=builder), load=Mock(side_effect=AssertionError('no download')),
                           as_numpy=lambda records: ((image, label) for label in (0, 1) for _ in range(13779)))
    monkeypatch.setitem(sys.modules, 'tensorflow_datasets', tfds)
    result = prepare_cell_source(resolve_source_config(capstone_root=tmp_path, environ={}), verify_only=True)
    assert result['status'] == 'ALREADY_DOWNLOADED'
    assert result['images'] == 27558
    tfds.load.assert_not_called()


def test_missing_cell_verify_only_never_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from src.malaria_dl.data import cell_source
    monkeypatch.setattr(cell_source, 'get_tfds_data_dir', lambda: tmp_path / 'absent')
    tfds = SimpleNamespace(load=Mock(side_effect=AssertionError('no network')))
    monkeypatch.setitem(sys.modules, 'tensorflow_datasets', tfds)
    with pytest.raises(full.SourceError, match='INTEGRITY_FAIL'):
        prepare_cell_source(resolve_source_config(capstone_root=tmp_path, environ={}), verify_only=True)
    tfds.load.assert_not_called()
    assert not (tmp_path / 'absent').exists()
