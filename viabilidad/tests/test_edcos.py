from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from modelo_edcos import DIMENSIONES_EDCO,cargar_edcos,validar_ficha

class EdcosTest(unittest.TestCase):
    def setUp(self):
        self.ficha=cargar_edcos()[0]

    def test_filtro_institucion_separa_programas_y_valida_pais(self):
        from modelo_edcos import programas_institucion
        cr=deepcopy(self.ficha)
        cr.update(id='programa_cr',institucion_id='ulatina_cr')
        cr['brief']['pais']='Costa Rica'
        records=[self.ficha,cr]
        self.assertEqual([f['id'] for f in programas_institucion(records,'udla_ec')],[self.ficha['id']])
        self.assertEqual([f['id'] for f in programas_institucion(records,'ulatina_cr')],['programa_cr'])
        cr['brief']['pais']='Ecuador'
        with self.assertRaises(ValueError):validar_ficha(cr)

    def test_estudios_cr_completos_independientes_sin_datos_ecuador(self):
        records=[f for f in cargar_edcos() if f['institucion_id']=='ulatina_cr']
        self.assertEqual(len(records),2)
        for ficha in records:
            self.assertEqual(validar_ficha(ficha)['evaluados'],5)
            self.assertIsNotNone(validar_ficha(ficha)['total'])
            self.assertEqual(ficha['brief']['pais'],'Costa Rica')
            self.assertEqual(ficha['brief']['duracion'],'1.5 cuatrimestres')
            self.assertIsNone(ficha['brief']['horas_totales'])
            self.assertEqual(set(ficha['evidencia_visual']),{r[0] for r in DIMENSIONES_EDCO})
            self.assertEqual(ficha['evidencia_visual']['sector']['origen'],'bccr')
            self.assertFalse(ficha['evidencia_visual']['demanda']['serie'])
            sources={s['id'] for s in ficha['fuentes']}
            for criterion in ficha['evaluacion'].values():
                self.assertTrue(set(criterion['fuentes'])<=sources)
                self.assertTrue(set(criterion['fuentes'])-{'brief'})
            self.assertTrue(any(o.get('precio_verificado') for o in ficha['ofertas']))
            self.assertTrue(all(p['pais']=='Costa Rica' for p in ficha['evidencia_visual']['empleabilidad']['publicaciones']))
            self.assertNotIn('sri_excel',sources)

    def test_cr_monedas_y_sector_no_se_mezclan(self):
        from graficos_edcos import grafico_dimension,ofertas_precio,monedas_precio
        records={f['id']:f for f in cargar_edcos()}
        tea=records['tea_integral_cr'];people=records['people_analytics_cr']
        self.assertEqual(monedas_precio(tea),['CRC'])
        self.assertEqual(monedas_precio(people),['USD'])
        tea_prices=grafico_dimension(tea,'precio')
        self.assertEqual(list(tea_prices.data[0].y),[60000,16000,15000])
        self.assertIn('CRC',tea_prices.layout.yaxis.title.text)
        self.assertNotIn(38300,list(tea_prices.data[0].y))
        people_prices=grafico_dimension(people,'precio')
        self.assertEqual(list(people_prices.data[0].y),[1000,145,250,290,450])
        mixed=deepcopy(people)
        mixed['ofertas'].append(dict(institucion='Referencia CRC de prueba',tipo='Institucional',precio_crc=50000,precio_usd=None,precio_verificado=True,estado='Prueba'))
        self.assertEqual(monedas_precio(mixed),['USD','CRC'])
        self.assertEqual(list(grafico_dimension(mixed,'precio').data[0].y),[1000,145,250,290,450])
        mixed['evidencia_visual']['precio']['moneda']='CRC'
        self.assertEqual(list(grafico_dimension(mixed,'precio').data[0].y),[50000])
        for f in [tea,people]:
            sector=grafico_dimension(f,'sector')
            self.assertEqual(len(sector.data),1)
            self.assertEqual(len(sector.data[0].x),44)
            self.assertEqual(sector.data[0].x[0],'2023-01-01')
            self.assertEqual(sector.data[0].x[-1],'2026-08-01')
            self.assertIn('2022',sector.layout.yaxis.title.text)
            self.assertEqual(f['evidencia_visual']['sector']['base'],2022)
            self.assertNotIn('USD',sector.layout.yaxis.title.text)
            sources={s['id'] for s in f['fuentes']}
            self.assertTrue(all(o['fuente'] in sources for o in f['ofertas']))
            self.assertTrue(all(set(e['fuentes'])<=sources for e in f['evidencia_visual'].values()))
            skills=f['evidencia_visual']['empleabilidad']
            for row in skills['habilidades']:
                count=sum(row['id'] in p['habilidades'] for p in skills['publicaciones'])
                self.assertEqual(row['menciones'],count)
                self.assertAlmostEqual(row['porcentaje'],100*count/len(skills['publicaciones']))

    def test_imae_vigente_usa_niveles_sin_mezclar_variaciones_o_bases(self):
        import json
        from actualizacion_bccr_edcos import ARCHIVO,extraer_serie
        raw=json.loads(ARCHIVO.read_text(encoding='utf-8'))
        tea=extraer_serie(raw,94986)
        people=extraer_serie(raw,94984)
        self.assertEqual(tea['serie_indice'][-1]['valor'],107.57)
        self.assertEqual(people['serie_indice'][-1]['valor'],128.77)
        self.assertEqual(tea['periodo_hasta'],'2026-08-01')
        wrong=deepcopy(raw)
        wrong['informacionDelCuadro']['subTituloEspanol']='Serie original (2017=100)'
        with self.assertRaises(ValueError):extraer_serie(wrong,94986)
        for ficha in cargar_edcos():
            if ficha['institucion_id']=='ulatina_cr':
                for evidence in ficha['evidencia_visual'].values():
                    self.assertEqual(evidence['fecha_consulta'],'2026-10-26')
                    self.assertTrue(evidence['actualidad'])

    def test_investigacion_completa_y_ponderada(self):
        r=validar_ficha(self.ficha)
        self.assertEqual(r['cobertura'],100)
        self.assertEqual(r['evaluados'],5)
        self.assertAlmostEqual(r['total'],64.1)
        self.assertEqual(r['estado'],'Viabilidad condicionada')
        self.assertTrue(all(c.get('nivel_evidencia') for c in self.ficha['evaluacion'].values()))

    def test_brief_no_inventa_precio_horas_o_tamano(self):
        self.assertNotIn('precio_propuesto_usd',self.ficha['brief'])
        self.assertIsNone(self.ficha['brief']['horas_totales'])
        self.assertIsNone(self.ficha['audiencia_propuesta']['tamano'])

    def test_pendientes_no_generan_total_ni_cero(self):
        f=deepcopy(self.ficha)
        for key in ['demanda','empleabilidad','precio','sector']:f['evaluacion'][key]['puntaje']=None
        r=validar_ficha(f)
        self.assertIsNone(r['total'])
        self.assertEqual(r['cobertura'],28)
        self.assertEqual(r['evaluados'],1)
        self.assertIsNone(r['filas'][0]['aporte'])

    def test_pesos_acordados_y_calculo_completo(self):
        from modelo import BLOQUES
        self.assertEqual([row[1] for row in DIMENSIONES_EDCO],BLOQUES)
        self.assertEqual([row[2] for row in DIMENSIONES_EDCO],[30,22,28,12,8])
        f=deepcopy(self.ficha)
        for c in f['evaluacion'].values():c['puntaje']=80
        self.assertAlmostEqual(validar_ficha(f)['total'],80)

    def test_cero_observado_es_distinto_de_no_evaluado(self):
        f=deepcopy(self.ficha)
        for key in ['demanda','empleabilidad','precio','sector']:f['evaluacion'][key]['puntaje']=None
        f['evaluacion']['demanda']['puntaje']=0
        r=validar_ficha(f)
        self.assertEqual(r['cobertura'],58)
        self.assertEqual(r['filas'][0]['aporte'],0)
        self.assertIsNone(r['total'])

    def test_fuentes_y_oferta_propia(self):
        f=deepcopy(self.ficha)
        own=next(o for o in f['ofertas'] if o['tipo']=='Oferta propia')
        own['competidor_directo']=True
        with self.assertRaises(ValueError):validar_ficha(f)
        f=deepcopy(self.ficha)
        f['evaluacion']['competencia']['fuentes']=['fuente_inexistente']
        with self.assertRaises(ValueError):validar_ficha(f)

    def test_puntaje_sin_sustento_no_se_admite(self):
        f=deepcopy(self.ficha)
        f['evaluacion']['competencia']['fuentes']=[]
        with self.assertRaises(ValueError):validar_ficha(f)

    def test_navegacion_y_retorno_a_carreras(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['apartado']='Educación continua'
        app.run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key='edco_programa').value,self.ficha['nombre'])
        self.assertEqual([t.label for t in app.tabs],['Diagnóstico EdCo','Oferta y plataformas','Cálculo y evidencia','Brief del proponente'])
        self.assertFalse(any('COBERTURA DE EVALUACIÓN' in m.value for m in app.markdown))
        self.assertFalse(any('PRECIO PROPUESTO' in m.value for m in app.markdown))
        self.assertFalse(any('? &nbsp; Sin verificar' in m.value for m in app.markdown))
        self.assertTrue(any('REFERENCIAS DE PRECIO' in m.value for m in app.markdown))
        app.radio(key='edco_periodo_sri').set_value('Totales anuales · 2023–2026 (2026 hasta agosto)').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        app.multiselect(key='edco_skill_areas').set_value(['UX y experiencia']).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any(m.label=='Publicaciones identificadas' and m.value=='5' for m in app.metric))
        app.multiselect(key='edco_skill_areas').set_value([]).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertTrue(any(m.label=='Publicaciones identificadas' and m.value=='0' for m in app.metric))
        app.multiselect(key='edco_comp_tipos').set_value([]).run(timeout=30)
        self.assertEqual(len(app.exception),0)
        app.multiselect(key='edco_comp_tipos').set_value(['Institucional','Plataforma','Oferta propia']).run(timeout=30)
        app.checkbox(key='edco_comp_inscripcion').check().run(timeout=30)
        self.assertEqual(len(app.exception),0)
        app.selectbox(key='edco_institucion').set_value('ulatina_cr').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        cr=[f for f in cargar_edcos() if f['institucion_id']=='ulatina_cr']
        self.assertEqual(len(cr),2)
        self.assertEqual(set(app.selectbox(key='edco_programa').options),{f['nombre'] for f in cr})
        for ficha in cr:
            app.selectbox(key='edco_programa').set_value(ficha['nombre']).run(timeout=30)
            self.assertEqual(len(app.exception),0)
            self.assertTrue(app.checkbox(key='edco_eval_demanda').value)
            self.assertEqual(app.number_input(key='edco_score_competencia').value,ficha['evaluacion']['competencia']['puntaje'])
            self.assertTrue(any('ULatina' in item.value for item in app.caption))
            self.assertFalse(any('SRI' in item.value for item in app.caption))
            self.assertFalse(any('Neuro-UX' in item.value for item in app.markdown))
        app.selectbox(key='edco_institucion').set_value('udla_ec').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(app.selectbox(key='edco_programa').value,self.ficha['nombre'])
        app.radio(key='apartado').set_value('Carreras').run(timeout=30)
        self.assertEqual(len(app.exception),0)
        self.assertEqual(len(app.tabs),12)

    def test_recarga_vista_antigua_y_sesion_sin_campo_eliminado(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        old=deepcopy(self.ficha)
        old['brief']['precio_propuesto_usd']=999
        old['version_investigacion']='antigua'
        old['evaluacion']['competencia']['puntaje']=60
        old['evaluacion']['competencia']['estado']='Revisión manual en sesión'
        old['evaluacion']['sector']['puntaje']=None
        old['evaluacion']['empleabilidad']['puntaje']=None
        old['evaluacion']['formato']={'puntaje':65,'fuentes':['brief'],'justificacion':'Valoración antigua de modalidad'}
        old['evaluacion']['audiencia']={'puntaje':80,'fuentes':['brief'],'justificacion':'Valoración antigua de audiencia'}
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'))
        app.session_state['apartado']='Educación continua'
        app.session_state['edco_revision_'+self.ficha['id']]=old
        with patch('edcos_vista.render_edcos',side_effect=KeyError('precio_propuesto_usd')) as stale:
            app.run(timeout=30)
            self.assertEqual(len(app.exception),0)
            stale.assert_not_called()
        self.assertTrue(any('REFERENCIAS DE PRECIO' in m.value for m in app.markdown))
        self.assertFalse(any('PRECIO PROPUESTO' in m.value for m in app.markdown))
        self.assertEqual(app.number_input(key='edco_score_competencia').value,60)
        self.assertTrue(app.checkbox(key='edco_eval_sector').value)
        self.assertTrue(app.checkbox(key='edco_eval_empleabilidad').value)

    def test_radar_pentagono_y_faltantes_sin_cero(self):
        from graficos_edcos import radar_edco,EJES_EDCO
        f=deepcopy(self.ficha)
        for key in ['demanda','empleabilidad','precio','sector']:f['evaluacion'][key]['puntaje']=None
        fig=radar_edco(validar_ficha(f))
        self.assertEqual(list(fig.data[0].theta),EJES_EDCO+[EJES_EDCO[0]])
        self.assertEqual(list(fig.data[0].r),[None,None,55,None,None,None])
        self.assertEqual(list(fig.data[1].r),[100]*6)
        self.assertFalse(fig.data[0].connectgaps)

    def test_graficos_evidencia_no_mezclan_precios_ni_inventan_series(self):
        from graficos_edcos import grafico_dimension
        demand=grafico_dimension(self.ficha,'demanda')
        self.assertEqual(list(demand.data[0].x),[214192,4441,1235])
        self.assertFalse(self.ficha['evidencia_visual']['demanda']['serie'])
        prices=grafico_dimension(self.ficha,'precio')
        self.assertEqual(prices.data[0].type,'box')
        self.assertEqual(list(prices.data[0].y),[650,1200,377,300,30])
        self.assertIn('UISEK',list(prices.data[1].text))
        sector=grafico_dimension(self.ficha,'sector')
        self.assertEqual(list(sector.data[0].x),['2023 · ene–ago','2024 · ene–ago','2025 · ene–ago','2026 · ene–ago'])
        self.assertAlmostEqual(sector.data[0].y[-1],2962292.75)
        self.assertEqual(len(grafico_dimension(self.ficha,'competencia').data),0)
        skills=grafico_dimension(self.ficha,'empleabilidad')
        self.assertEqual(len(skills.data[0].x),10)
        self.assertTrue(all(t.endswith('%') for t in skills.data[0].text))
        self.assertAlmostEqual(skills.data[0].x[0],100*20/22)
        for key,_,_ in DIMENSIONES_EDCO:
            self.assertTrue(self.ficha['evidencia_visual'][key]['fuentes'])

    def test_importacion_verifica_comparabilidad_y_graficos(self):
        from io import StringIO
        from datos_visuales_edcos import leer_evidencia
        from graficos_edcos import grafico_dimension
        f=deepcopy(self.ficha)
        key,rows=leer_evidencia(StringIO('programa,busquedas,competidores,territorio,consulta,fuente\nPrueba,80,2,EC,mismo periodo,Fuente de prueba\n'),'competencia',f['brief']['ciiu'])
        f['evidencia_visual']['competencia'][key]=rows
        self.assertEqual(list(grafico_dimension(f,'competencia').data[0].x),[80])
        invalid=[('competencia','programa,busquedas,competidores,territorio,consulta,fuente\nPrueba,101,2,EC,test,fuente\n'),('competencia','programa,busquedas,competidores,territorio,consulta,fuente\nPrueba,80,2.5,EC,test,fuente\n'),('demanda','fecha,termino,indice,territorio,consulta,fuente\n2024-01-01,A,40,EC,test,fuente\n2024-02-01,B,30,EC,test,fuente\n'),('sector','anio,naturales,sociedades,ciiu,meses,fuente\n2024,10,20,OTRO,12,fuente\n')]
        for dimension,csv in invalid:
            with self.assertRaises(ValueError):leer_evidencia(StringIO(csv),dimension,f['brief']['ciiu'])
        field,rows=leer_evidencia(StringIO('anio,naturales,sociedades,ciiu,meses,fuente\n2023,10,20,M7320.01,12,prueba\n2024,11,22,M7320.01,12,prueba\n'),'sector','M7320.01')
        f['evidencia_visual']['sector'][field]=rows
        self.assertEqual(list(grafico_dimension(f,'sector').data[1].y),[20,22])
        self.assertEqual(validar_ficha(f)['total'],validar_ficha(self.ficha)['total'])

    def test_muestra_linkedin_trazable_y_precios_separados(self):
        from graficos_edcos import ofertas_precio
        e=self.ficha['evidencia_visual']['empleabilidad']
        self.assertEqual(len({r['id'] for r in e['publicaciones']}),22)
        for skill in e['habilidades']:
            mentions=sum(skill['id'] in r['habilidades'] for r in e['publicaciones'])
            self.assertEqual(skill['menciones'],mentions)
            self.assertEqual(skill['porcentaje'],100*mentions/len(e['publicaciones']))
        f=deepcopy(self.ficha)
        f['evidencia_visual']['precio']['incluir_historicas']=True
        self.assertEqual([o['precio_usd'] for o in ofertas_precio(f)],[650,1200,377,300,30])
        self.assertNotIn(20,[o['precio_usd'] for o in ofertas_precio(f)])

    def test_habilidades_filtros_deduplicacion_y_denominador(self):
        from habilidades_edcos import resumir_habilidades
        e=deepcopy(self.ficha['evidencia_visual']['empleabilidad'])
        first=deepcopy(e['publicaciones'][0])
        e['publicaciones'].append(first)
        repost=deepcopy(first);repost['identificador_linkedin']='republicacion';repost['id']='republicacion'
        e['publicaciones'].append(repost)
        self.assertEqual(resumir_habilidades(e)['total'],22)
        ux=resumir_habilidades(e,['UX y experiencia'])
        self.assertEqual(ux['total'],5)
        self.assertEqual(next(s['menciones'] for s in ux['habilidades'] if s['id']=='usabilidad'),5)
        self.assertEqual(next(s['porcentaje'] for s in ux['habilidades'] if s['id']=='ia'),20)
        empty=resumir_habilidades(e,[])
        self.assertEqual(empty['total'],0)
        self.assertTrue(all(s['porcentaje'] is None for s in empty['habilidades']))
        # IA en beneficios de capacitación no se codifica como requisito de Devsu.
        self.assertNotIn('ia',next(r for r in e['publicaciones'] if r['empresa']=='Devsu')['habilidades'])

    def test_extraccion_sri_exacta_y_periodos_comparables(self):
        import tempfile
        import openpyxl
        from investigacion_sri_edcos import extraer_ventas_sri
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'ventas.xlsx'
            w=openpyxl.Workbook();s=w.active;s.title='Ventas SRI'
            s.append(['actividad','anio','mes','n411','s411','n413','s413'])
            for year in [2024,2025]:
                for month in range(1,13 if year==2024 else 9):
                    s.append(['M732001',year,month,10,20,1,2])
                    s.append(['C273201',year,month,999,999,999,999])
            w.save(path);w.close()
            r=extraer_ventas_sri(path,'M7320.01')
            self.assertEqual(len(r['mensual']),20)
            self.assertEqual([a['meses'] for a in r['ventas']],[8,8])
            self.assertEqual([a['naturales'] for a in r['ventas']],[88,88])
            self.assertEqual(r['ventas_anuales'][0]['sociedades'],264)
            self.assertEqual(len(r['ventas_anuales']),1)

    def test_contenidos_desconocidos_y_portafolio_no_inflan_competencia(self):
        from competencia_edcos import filas_contenidos,resumen_contenidos,grafico_contenidos,posicionamiento
        rows=filas_contenidos(self.ficha)
        summary=resumen_contenidos(self.ficha,rows)
        self.assertEqual(summary['total'],10)
        self.assertEqual(summary['sin_verificar'],0)
        self.assertEqual(summary['conteos']['biometria'],1)
        self.assertEqual(summary['conteos']['laboratorio'],0)
        chart=grafico_contenidos(self.ficha,rows)
        self.assertTrue(all(v==1 for v in chart.data[0].z[0]))
        unknown=deepcopy(rows)
        unknown[0]['revision']['contenidos']['biometria']=None
        unknown_chart=grafico_contenidos(self.ficha,unknown)
        self.assertTrue(all('?' not in texts for texts in unknown_chart.data[0].text))
        self.assertIn(-1,list(unknown_chart.data[0].z[1]))
        self.assertNotIn('UISEK',list(chart.data[0].y))
        self.assertFalse(any('Sudamericano' in label for label in chart.data[0].y))
        own=next(r for r in rows if r['tipo']=='Oferta propia')
        self.assertTrue(own['revision']['contenidos']['biometria'])
        self.assertFalse(own['revision']['contenidos']['laboratorio'])
        fig,missing=posicionamiento(self.ficha,rows)
        self.assertEqual(sum(len(t.x) for t in fig.data),5)
        self.assertEqual(next(t.marker.color for t in fig.data if t.name=='Plataformas'),'#bd8a40')
        self.assertTrue(any(r['institucion']=='Universidad Europea' for r in missing))
        self.assertFalse(any(r['institucion']=='UISEK' for r in missing))
        filtered=filas_contenidos(self.ficha,[],False)
        self.assertEqual(resumen_contenidos(self.ficha,filtered)['total'],0)
        self.assertEqual(len(grafico_contenidos(self.ficha,filtered).data[0].y),1)

if __name__=='__main__':unittest.main()
