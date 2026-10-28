-- Content/multiplicity fingerprint, not a substitute for EXCEPT ALL assertions.
SET DateStyle='ISO,YMD';
SET TimeZone='UTC';
SELECT format(
 'SELECT %L, count(*), encode(sha256(convert_to(coalesce(string_agg(h,%L ORDER BY h),%L),%L)),%L) FROM (SELECT encode(sha256(convert_to((to_jsonb(t) %s)::text,%L)),%L) h FROM %I.%I t) r',
 n.nspname||'.'||c.relname,'','','UTF8','hex',
 CASE WHEN n.nspname='core' AND c.relname='check_results' THEN '- ''checked_at''' ELSE '' END,
 'UTF8','hex',n.nspname,c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('raw','core','mart') AND c.relkind IN ('r','p','v','m')
ORDER BY n.nspname,c.relname
\gexec

-- Object definitions, identified by names/signatures rather than unstable OIDs.
WITH definitions AS (
 SELECT n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')#function' AS object_name,
        pg_get_functiondef(p.oid) AS definition
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 WHERE n.nspname IN ('raw','core','mart') AND p.prokind IN ('f','p')
 UNION ALL
 SELECT n.nspname||'.'||c.relname||'#view',pg_get_viewdef(c.oid,false)
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('raw','core','mart') AND c.relkind IN ('v','m')
 UNION ALL
 SELECT n.nspname||'.'||c.relname||'#constraint:'||k.conname,pg_get_constraintdef(k.oid,false)
 FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('raw','core','mart')
 UNION ALL
 SELECT n.nspname||'.'||c.relname||'#column:'||a.attname,
        format('%s:%s:%s:%s',a.attnum,format_type(a.atttypid,a.atttypmod),a.attnotnull,pg_get_expr(d.adbin,d.adrelid))
 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
 LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum
 WHERE n.nspname IN ('raw','core','mart') AND a.attnum>0 AND NOT a.attisdropped
 AND c.relkind IN ('r','p','v','m')
 UNION ALL
 SELECT n.nspname||'.'||c.relname||'#index',pg_get_indexdef(c.oid)
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('raw','core','mart') AND c.relkind='i'
)
SELECT object_name,1,encode(sha256(convert_to(definition,'UTF8')),'hex')
FROM definitions ORDER BY object_name;
