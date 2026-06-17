export type LegalBlock = { type: 'p'; text: string } | { type: 'list'; items: string[] }

export interface LegalSection {
  heading: string
  blocks: LegalBlock[]
}

export interface LegalContent {
  title: string
  lastUpdated: string
  intro: string
  sections: LegalSection[]
}

const CONTACT_EMAIL = 'ventas@codelabsecuador.com'
const LAST_UPDATED = '17 de junio de 2026'

export const termsContent: LegalContent = {
  title: 'Términos y Condiciones de Uso',
  lastUpdated: LAST_UPDATED,
  intro:
    'Estos Términos y Condiciones regulan el acceso y uso de CodeLabs Billing (el "Servicio"), ' +
    'una plataforma SaaS de facturación electrónica operada por CodeLabs Ecuador ("CodeLabs", ' +
    '"nosotros"). Al crear una cuenta o usar el Servicio, aceptas estos términos en su totalidad.',
  sections: [
    {
      heading: '1. Descripción del servicio',
      blocks: [
        {
          type: 'p',
          text:
            'CodeLabs Billing permite a empresas ecuatorianas emitir, firmar electrónicamente y ' +
            'gestionar comprobantes autorizados por el Servicio de Rentas Internas (SRI), entre ' +
            'ellos:',
        },
        {
          type: 'list',
          items: [
            'Facturas electrónicas',
            'Notas de crédito y notas de débito',
            'Comprobantes de retención',
            'Guías de remisión',
          ],
        },
        {
          type: 'p',
          text:
            'El Servicio incluye un ambiente de pruebas para validar la integración antes de operar ' +
            'en producción, y un panel de administración multiempresa (multitenant) para gestionar ' +
            'usuarios, clientes y documentos.',
        },
      ],
    },
    {
      heading: '2. Registro y cuentas',
      blocks: [
        {
          type: 'p',
          text:
            'Para usar el Servicio debes registrar tu empresa con datos veraces, incluyendo el RUC ' +
            'y la información tributaria correspondiente. Eres responsable de mantener la ' +
            'confidencialidad de tus credenciales de acceso y de toda actividad que ocurra en tu ' +
            'cuenta. Notifícanos de inmediato ante cualquier uso no autorizado.',
        },
        {
          type: 'p',
          text:
            'Cada cuenta corresponde a una sola empresa (tenant). La administración de múltiples ' +
            'usuarios dentro de una misma cuenta, con distintos niveles de acceso (propietario, ' +
            'administrador, solo lectura), está disponible según el plan contratado.',
        },
      ],
    },
    {
      heading: '3. Planes, suscripciones y pagos',
      blocks: [
        {
          type: 'p',
          text:
            'El acceso al Servicio se ofrece mediante planes de suscripción recurrente (mensual o ' +
            'anual), con límites de documentos, usuarios y locales según el plan elegido. Los ' +
            'precios y características de cada plan se muestran en nuestra página de precios antes ' +
            'de la contratación.',
        },
        {
          type: 'p',
          text:
            'Los pagos son procesados mediante dLocal Go como pasarela de pagos. CodeLabs no ' +
            'almacena números de tarjeta ni datos bancarios completos; esos datos se gestionan en ' +
            'los campos seguros de la pasarela durante el checkout.',
        },
        {
          type: 'p',
          text:
            'La renovación de la suscripción se gestiona mediante el flujo de pago disponible en ' +
            'la plataforma antes del vencimiento del período contratado. Cualquier cambio de ' +
            'precios será notificado con antelación razonable y no afectará a períodos ya pagados.',
        },
      ],
    },
    {
      heading: '4. Certificados digitales y firma electrónica',
      blocks: [
        {
          type: 'p',
          text:
            'Para firmar electrónicamente tus comprobantes, debes cargar tu certificado de firma ' +
            'digital (archivo .p12) emitido por una entidad certificadora autorizada en Ecuador. ' +
            'CodeLabs no emite ni gestiona certificados digitales en tu nombre; eres responsable de ' +
            'mantener tu certificado vigente y de su renovación oportuna.',
        },
        {
          type: 'p',
          text:
            'El Servicio almacena tu certificado de forma cifrada y lo utiliza exclusivamente para ' +
            'firmar los documentos que generes dentro de tu cuenta. Te notificaremos por correo ' +
            'cuando tu certificado esté próximo a vencer.',
        },
      ],
    },
    {
      heading: '5. Uso aceptable',
      blocks: [
        {
          type: 'p',
          text: 'Al usar el Servicio, te comprometes a no:',
        },
        {
          type: 'list',
          items: [
            'Emitir comprobantes con información falsa o que no correspondan a operaciones reales.',
            'Usar el Servicio para actividades ilegales, fraudulentas o que infrinjan normativa ' +
              'tributaria vigente.',
            'Intentar vulnerar la seguridad de la plataforma, acceder a cuentas de otras empresas ' +
              'o realizar ingeniería inversa sobre el Servicio.',
            'Sobrecargar deliberadamente la infraestructura mediante uso automatizado fuera de los ' +
              'límites de tu plan o de la API.',
          ],
        },
      ],
    },
    {
      heading: '6. Disponibilidad y soporte',
      blocks: [
        {
          type: 'p',
          text:
            'Trabajamos para mantener el Servicio disponible de forma continua, pero no garantizamos ' +
            'disponibilidad ininterrumpida. Pueden existir ventanas de mantenimiento programado, que ' +
            'comunicaremos con antelación cuando sea posible. El soporte se brinda por los canales ' +
            'indicados en el panel según el plan contratado.',
        },
      ],
    },
    {
      heading: '7. Propiedad intelectual',
      blocks: [
        {
          type: 'p',
          text:
            'CodeLabs es titular de todos los derechos sobre la plataforma, su código, diseño y ' +
            'marca. Tú conservas la propiedad de los datos de tu empresa, tus clientes y los ' +
            'documentos que generes a través del Servicio.',
        },
      ],
    },
    {
      heading: '8. Limitación de responsabilidad',
      blocks: [
        {
          type: 'p',
          text:
            'El Servicio se proporciona "tal cual". En la medida permitida por la ley, CodeLabs no ' +
            'será responsable por daños indirectos, pérdida de ingresos o de información derivados ' +
            'del uso del Servicio. Nuestra responsabilidad total frente a ti se limita al monto ' +
            'pagado por la suscripción durante los tres meses previos al reclamo.',
        },
        {
          type: 'p',
          text:
            'CodeLabs no es responsable por rechazos, demoras o indisponibilidad de los sistemas del ' +
            'SRI, ni por errores derivados de información incorrecta ingresada por el usuario.',
        },
      ],
    },
    {
      heading: '9. Suspensión y terminación',
      blocks: [
        {
          type: 'p',
          text:
            'Podemos suspender o cancelar tu cuenta en caso de incumplimiento de estos términos, ' +
            'falta de pago o uso fraudulento del Servicio. Puedes cancelar tu suscripción en ' +
            'cualquier momento; tu acceso se mantendrá hasta el final del período ya pagado. Tras la ' +
            'cancelación, tus datos se conservan según lo descrito en nuestra Política de ' +
            'Privacidad antes de su eliminación definitiva.',
        },
      ],
    },
    {
      heading: '10. Modificaciones a estos términos',
      blocks: [
        {
          type: 'p',
          text:
            'Podemos actualizar estos términos ocasionalmente. Te notificaremos los cambios ' +
            'importantes por correo electrónico o dentro del panel. El uso continuado del Servicio ' +
            'tras la entrada en vigencia de los cambios implica su aceptación.',
        },
      ],
    },
    {
      heading: '11. Ley aplicable y jurisdicción',
      blocks: [
        {
          type: 'p',
          text:
            'Estos términos se rigen por las leyes de la República del Ecuador. Cualquier disputa ' +
            'relacionada con el Servicio se someterá a los jueces competentes del Ecuador, sin ' +
            'perjuicio de los mecanismos de soporte o resolución de disputas que correspondan al ' +
            'pago procesado por la pasarela.',
        },
      ],
    },
    {
      heading: '12. Contacto',
      blocks: [
        {
          type: 'p',
          text: `Para preguntas sobre estos términos, escríbenos a ${CONTACT_EMAIL}.`,
        },
      ],
    },
  ],
}

export const privacyContent: LegalContent = {
  title: 'Política de Privacidad',
  lastUpdated: LAST_UPDATED,
  intro:
    'En CodeLabs Billing nos tomamos en serio la protección de tu información y la de tus ' +
    'clientes. Esta política explica qué datos recopilamos, cómo los usamos, con quién los ' +
    'compartimos y qué derechos tienes sobre ellos.',
  sections: [
    {
      heading: '1. Responsable del tratamiento',
      blocks: [
        {
          type: 'p',
          text:
            `CodeLabs Ecuador es responsable del tratamiento de los datos personales recopilados a ` +
            `través de CodeLabs Billing. Puedes contactarnos en ${CONTACT_EMAIL} para cualquier ` +
            'consulta relacionada con esta política.',
        },
      ],
    },
    {
      heading: '2. Datos que recopilamos',
      blocks: [
        {
          type: 'list',
          items: [
            'Datos de cuenta: nombre, correo electrónico y rol del usuario que administra la cuenta.',
            'Datos de la empresa (tenant): razón social, RUC, dirección y demás información ' +
              'tributaria necesaria para emitir comprobantes electrónicos.',
            'Datos de tus clientes: la información que registras en tu catálogo de clientes para ' +
              'facturarles (identificación, nombre, dirección, contacto).',
            'Certificados de firma electrónica (.p12) y su contraseña, almacenados de forma cifrada ' +
              'y usados exclusivamente para firmar tus documentos.',
            'Datos de uso: registros técnicos de acceso y operación del Servicio, necesarios para ' +
              'seguridad y soporte.',
            'Datos de pago: gestionados directamente por dLocal Go como pasarela de pagos. ' +
              'CodeLabs no almacena números de tarjeta ni datos bancarios completos.',
          ],
        },
      ],
    },
    {
      heading: '3. Cómo usamos tus datos',
      blocks: [
        {
          type: 'list',
          items: [
            'Proveer el Servicio: autenticación, emisión y firma de comprobantes, gestión de ' +
              'clientes y generación de reportes.',
            'Enviar comunicaciones transaccionales: confirmaciones de registro, códigos OTP, ' +
              'alertas de vencimiento de certificados y notificaciones de tu cuenta.',
            'Cumplir obligaciones legales y tributarias frente al SRI y otras autoridades ' +
              'ecuatorianas.',
            'Mejorar el Servicio y prevenir fraude o uso indebido de la plataforma.',
          ],
        },
        {
          type: 'p',
          text: 'No vendemos tus datos ni los de tus clientes a terceros.',
        },
      ],
    },
    {
      heading: '4. Base legal del tratamiento',
      blocks: [
        {
          type: 'p',
          text:
            'Tratamos tus datos para la ejecución del contrato de suscripción (Términos y ' +
            'Condiciones), para cumplir obligaciones legales tributarias, y por interés legítimo en ' +
            'mantener la seguridad y el correcto funcionamiento del Servicio.',
        },
      ],
    },
    {
      heading: '5. Con quién compartimos información',
      blocks: [
        {
          type: 'list',
          items: [
            'Amazon Web Services (AWS): proveedor de infraestructura donde se almacenan tus datos, ' +
              'bajo cifrado y controles de acceso.',
            'Amazon Cognito: servicio de autenticación que gestiona tus credenciales de acceso.',
            'Servicio de Rentas Internas (SRI): los comprobantes que emites se envían al SRI para ' +
              'su autorización, conforme a la normativa de facturación electrónica.',
            'dLocal Go: pasarela usada para procesar pagos de suscripción, bajo sus propios ' +
              'términos y políticas aplicables al checkout.',
            'Proveedores de correo electrónico transaccional, para el envío de notificaciones de tu ' +
              'cuenta.',
          ],
        },
      ],
    },
    {
      heading: '6. Transferencias internacionales',
      blocks: [
        {
          type: 'p',
          text:
            'La infraestructura principal del Servicio opera en la región de AWS Sudamérica (San ' +
            'Pablo, Brasil). Los datos de pago procesados por dLocal Go pueden tratarse en otras ' +
            'jurisdicciones conforme a sus políticas y salvaguardas como pasarela de pagos.',
        },
      ],
    },
    {
      heading: '7. Conservación y eliminación de datos',
      blocks: [
        {
          type: 'p',
          text:
            'Conservamos tus datos mientras tu cuenta esté activa. Si cancelas tu suscripción, ' +
            'aplicamos un proceso de baja lógica (soft delete) que preserva la información necesaria ' +
            'para cumplir obligaciones legales o tributarias (por ejemplo, comprobantes ya emitidos ' +
            'al SRI), y eliminamos de forma definitiva el resto de los datos transcurrido el plazo ' +
            'legal de retención aplicable.',
        },
      ],
    },
    {
      heading: '8. Seguridad de la información',
      blocks: [
        {
          type: 'list',
          items: [
            'Cifrado de datos en tránsito (HTTPS/TLS) y en reposo.',
            'Certificados de firma electrónica y credenciales sensibles almacenados cifrados, ' +
              'nunca en texto plano ni en registros (logs).',
            'Acceso a la información segregado por empresa (tenant): cada cuenta solo puede ver sus ' +
              'propios datos.',
            'Gestión de secretos mediante servicios dedicados, separados del código de la ' +
              'aplicación.',
          ],
        },
      ],
    },
    {
      heading: '9. Tus derechos',
      blocks: [
        {
          type: 'p',
          text:
            'Conforme a la Ley Orgánica de Protección de Datos Personales del Ecuador, puedes ' +
            'solicitar acceso, rectificación, actualización o eliminación de tus datos personales, ' +
            'así como oponerte a determinados tratamientos. Para ejercer estos derechos, ' +
            `escríbenos a ${CONTACT_EMAIL}.`,
        },
      ],
    },
    {
      heading: '10. Cookies y tecnologías similares',
      blocks: [
        {
          type: 'p',
          text:
            'Usamos almacenamiento local del navegador únicamente para mantener tu sesión iniciada ' +
            'y tus preferencias de la aplicación. No utilizamos cookies de publicidad ni de ' +
            'seguimiento de terceros.',
        },
      ],
    },
    {
      heading: '11. Cambios a esta política',
      blocks: [
        {
          type: 'p',
          text:
            'Podemos actualizar esta política para reflejar cambios en el Servicio o en la ' +
            'normativa aplicable. Notificaremos cambios relevantes por correo electrónico o dentro ' +
            'del panel.',
        },
      ],
    },
    {
      heading: '12. Contacto',
      blocks: [
        {
          type: 'p',
          text: `Para cualquier consulta sobre privacidad, escríbenos a ${CONTACT_EMAIL}.`,
        },
      ],
    },
  ],
}

export const refundContent: LegalContent = {
  title: 'Política de Reembolsos y Cancelaciones',
  lastUpdated: LAST_UPDATED,
  intro:
    'Esta política describe cómo funcionan las cancelaciones y reembolsos de las suscripciones ' +
    'de CodeLabs Billing.',
  sections: [
    {
      heading: '1. Naturaleza de las suscripciones',
      blocks: [
        {
          type: 'p',
          text:
            'Las suscripciones a CodeLabs Billing son de pago recurrente (mensual o anual) y se ' +
            'cobran por adelantado al inicio de cada período. El acceso a las funcionalidades y ' +
            'límites de uso corresponde al plan vigente durante ese período.',
        },
      ],
    },
    {
      heading: '2. Procesamiento de pagos',
      blocks: [
        {
          type: 'p',
          text:
            'Todos los cobros se procesan mediante dLocal Go como pasarela de pagos. CodeLabs no ' +
            'almacena números de tarjeta ni datos bancarios completos; el pago se confirma durante ' +
            'el checkout seguro de la pasarela.',
        },
      ],
    },
    {
      heading: '3. Reembolsos',
      blocks: [
        {
          type: 'p',
          text:
            'Si no estás satisfecho con el Servicio, puedes solicitar un reembolso dentro de los 14 ' +
            'días posteriores al primer cobro de una nueva suscripción. Evaluamos cada solicitud ' +
            'caso por caso, considerando el uso realizado de la cuenta durante ese período.',
        },
      ],
    },
    {
      heading: '4. Casos no reembolsables',
      blocks: [
        {
          type: 'list',
          items: [
            'Comprobantes electrónicos que ya fueron emitidos y autorizados por el SRI en ambiente ' +
              'de producción.',
            'Renovaciones de suscripciones posteriores al período inicial de evaluación.',
            'Cuentas suspendidas o canceladas por incumplimiento de los Términos y Condiciones.',
            'Períodos de uso ya transcurridos en suscripciones canceladas a mitad de ciclo.',
          ],
        },
      ],
    },
    {
      heading: '5. Cancelaciones',
      blocks: [
        {
          type: 'p',
          text:
            'Puedes cancelar tu suscripción en cualquier momento desde tu panel o contactando a ' +
            'soporte. La cancelación detiene la renovación automática; tu acceso se mantiene activo ' +
            'hasta el final del período ya pagado, sin reembolso proporcional por el tiempo restante ' +
            '(salvo lo indicado en la sección de reembolsos).',
        },
      ],
    },
    {
      heading: '6. Cambios de plan',
      blocks: [
        {
          type: 'p',
          text:
            'Puedes cambiar de plan en cualquier momento. Las mejoras (upgrade) se aplican de ' +
            'inmediato cuando el pago correspondiente se confirme. Las reducciones de plan ' +
            '(downgrade) se aplican a partir del siguiente ciclo de facturación.',
        },
      ],
    },
    {
      heading: '7. Cómo solicitar un reembolso o cancelación',
      blocks: [
        {
          type: 'p',
          text:
            `Escríbenos a ${CONTACT_EMAIL} indicando el correo de tu cuenta y el motivo de tu ` +
            'solicitud. Revisaremos el caso con la información del pago y el uso registrado en la ' +
            'cuenta.',
        },
      ],
    },
    {
      heading: '8. Contacto',
      blocks: [
        {
          type: 'p',
          text: `Para cualquier consulta sobre pagos, cancelaciones o reembolsos, escríbenos a ${CONTACT_EMAIL}.`,
        },
      ],
    },
  ],
}
