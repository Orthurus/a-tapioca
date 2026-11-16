import hashlib, io, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import atualizador as a

H1, H2 = "ab" * 32, "cd" * 32


class _R(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *x): pass


class Versoes(unittest.TestCase):
    def test_zeros_a_direita(self):
        self.assertEqual(a.vtuple("1.0"), a.vtuple("1.0.0"))

    def test_ordem(self):
        self.assertGreater(a.vtuple("v1.1.1"), a.vtuple("1.1"))
        self.assertGreater(a.vtuple("1.10"), a.vtuple("1.9"))

    def test_invalida(self):
        self.assertEqual(a.vtuple("x"), (0,))


class Hosts(unittest.TestCase):
    def test_permitidos(self):
        self.assertTrue(a._host_ok("https://github.com/x"))
        self.assertTrue(a._host_ok("https://objects.githubusercontent.com/x"))

    def test_bloqueados(self):
        for u in ("http://github.com", "https://evilgithub.com", "https://github.com.evil.io"):
            self.assertFalse(a._host_ok(u), u)


class Checksum(unittest.TestCase):
    def _lido(self, raw, nome="A_Tapioca.exe"):
        a._abrir = lambda url, timeout=15: _R(raw)
        return a._sha256_esperado("u", nome)

    def test_formatos(self):
        for raw in (f"{H1}  A_Tapioca.exe\r\n".encode(),
                    f"{H1}  A_Tapioca.exe\r\n".encode("utf-16"),
                    ("\ufeff" + f"{H1} *A_Tapioca.exe\n").encode(),
                    f"{H1}  A.Tapioca.exe\n".encode(),
                    f"{H1}\n".encode()):
            self.assertEqual(self._lido(raw), H1)

    def test_varios_hashes(self):
        raw = f"{H2}  outro.exe\n{H1}  A_Tapioca.exe\n".encode()
        self.assertEqual(self._lido(raw), H1)

    def test_sem_correspondencia(self):
        with self.assertRaises(a.ErroAtualizacao):
            self._lido(f"{H1}  x.exe\n{H2}  y.exe\n".encode())

    def test_lixo(self):
        with self.assertRaises(a.ErroAtualizacao):
            self._lido(b"lixo")


class Conferir(unittest.TestCase):
    def setUp(self):
        self.p = os.path.join(tempfile.mkdtemp(), "x.exe")
        with open(self.p, "wb") as f:
            f.write(b"MZ" + b"a" * 100)
        self.h = hashlib.sha256(open(self.p, "rb").read()).hexdigest()

    def test_ok_mesmo_com_tamanho_publicado_diferente(self):
        a._conferir(self.p, self.h, 999)

    def test_hash_errado(self):
        with self.assertRaises(a.ErroAtualizacao):
            a._conferir(self.p, "0" * 64, 102)

    def test_nao_executavel(self):
        with open(self.p, "wb") as f:
            f.write(b"<html>")
        with self.assertRaises(a.ErroAtualizacao):
            a._conferir(self.p, self.h, None)


class Bat(unittest.TestCase):
    def test_sem_timeout_e_escapa_percentual(self):
        b = a.gerar_bat(r"C:\Apps\100%\A.exe", r"C:\Apps\100%\A.exe.novo", marc=r"C:\T\m.ok")
        self.assertNotIn("timeout", b)
        self.assertIn("100%%", b)
        self.assertIn("rollback", b)


if __name__ == "__main__":
    unittest.main()
